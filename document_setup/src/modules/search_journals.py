import httpx
import io
import json
import re
import pandas as pd

from document_setup.src.configs.app import settings
from redis.asyncio import Redis
from utils import hash_blake3

JOURNAL_RANKING_KEY = "journal_ranking:{journal_name}:{year}"
JOURNAL_ISSN_KEY = "journal_issn:{journal_name}"


class SearchJournal():
    """
    Handles fetching, processing, and storing journal ranking information (SJR Quartile)
    and ISSN data from Scimago Journal & Country Rank.

    The data is stored in a Redis cache for quick retrieval.
    """
    def __init__(self, redis_client: Redis):
        """
        Initializes the SearchJournal class by establishing a connection
        to the Redis client.
        """
        self.redis_client = redis_client

    async def setup(self, last_updated: int = 1999):
        """
        Fetches journal ranking data from Scimago Journal & Country Rank for
        years starting from `last_updated` up to the current year defined in settings.

        Processes the data to extract journal titles, ISSNs, and SJR Best Quartiles,
        then stores this information in Redis. Journal names are normalized
        (lowercase, spaces replaced with underscores) for Redis keys.

        Args:
            last_updated (int, optional): The first year from which to fetch
                                          journal data. Defaults to 1999.
        """
        years_j = list(range(last_updated, settings.CURRENT_YEAR))
        df_jr = []
        for year in years_j:
            response = httpx.get(
                f"https://www.scimagojr.com/journalrank.php?year={year}&out=xls"
            )
            dfi = pd.read_csv(io.StringIO(response.content.decode('utf-8')), sep=';')
            dfi.columns = [
                re.sub(r"[0-9]+", "year", col) if i == 8 else col 
                for i, col in enumerate(dfi.columns)
            ]
            df_jr.append(dfi.assign(year=year))
        if len(df_jr):
            df_jr = pd.concat(df_jr, ignore_index=True)
            issn_dict = df_jr[["Title", "Issn"]].drop_duplicates().set_index('Title').to_dict()["Issn"]
            name: list[str] = []
            for key in issn_dict.keys():
                name.append(hash_blake3(key.replace(" ", "_").lower()))
            final_dict = dict(zip(name, list(issn_dict.values())))
            for key, value in final_dict.items():
                redis_key = JOURNAL_ISSN_KEY.format(journal_name=key)
                issn_bytes = await self.redis_client.get(redis_key)
                issn = value if value != "-" else "Unknown"
                if issn_bytes is None:
                    await self.redis_client.set(redis_key, json.dumps(issn))
            for row in range(len(df_jr)):
                key = JOURNAL_RANKING_KEY.format(
                    journal_name=hash_blake3(df_jr["Title"][row].replace(" ", "_").lower()), 
                    year=df_jr["year"][row])
                q_bytes = await self.redis_client.get(key)
                if q_bytes is None:
                    value = {"q": df_jr["SJR Best Quartile"][row] if df_jr["SJR Best Quartile"][row] != "-" else "Unknown"}
                    await self.redis_client.set(key, json.dumps(value))

    async def get_q_issn(self, journal_name: str, year: str) -> tuple[str, str]:
        """
        Retrieves the SJR Best Quartile (q) and ISSN for a given journal name and year
        from the Redis cache.

        The journal name is expected to be normalized (lowercase, spaces replaced
        with underscores) as used in the Redis keys.

        Args:
            journal_name (str): The normalized name of the journal.
            year (str): The publication year for which to retrieve the ranking.

        Returns:
            tuple[str, str]: A tuple containing the SJR Best Quartile and the ISSN.
                             Returns "Unknown" for either value if not found in the cache.
        """
        ranking_key = JOURNAL_RANKING_KEY.format(journal_name=hash_blake3(journal_name), year=year)
        q_bytes = await self.redis_client.get(ranking_key)
        if q_bytes is None:
            q = "Unknown"
        else:
            q_dict = json.loads(q_bytes)
            q = q_dict["q"]
        
        issn_key = JOURNAL_ISSN_KEY.format(journal_name=hash_blake3(journal_name))
        issn_bytes = await self.redis_client.get(issn_key)
        if issn_bytes is None:
            issn = "Unknown"
        else:
            issn = json.loads(issn_bytes)
        return q, issn