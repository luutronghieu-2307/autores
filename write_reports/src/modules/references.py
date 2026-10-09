import re


def edit_refs(   
    papers: list[dict], 
    content: str, 
    current_refs: list[str], 
    existing_refs: list[str], 
    references_style: str,
) -> tuple[str, list[str]]:
    if references_style in ["Vancouver", "IEEE"]:
        for ref in current_refs:
            if ref in existing_refs:
                content = content.replace(
                    f"[{ref}]", f"[{existing_refs.index(ref) + 1}]"
                )
            else:
                content = content.replace(
                    f"[{ref}]", f"[{len(existing_refs) + 1}]"
                )
                existing_refs.append(ref)
        content = content.replace("][", ",").replace("], [", ",")
        matches = re.findall(r'\[(\d+)\]', content)
        for match in matches:
            numbers = list(map(int, match.split(',')))
            sorted_numbers = sorted(numbers)
            sorted_str = '[' + ', '.join(map(str, sorted_numbers)) + ']'
            content = content.replace(f'[{match}]', sorted_str)
    else:
        used_refs: list[str] = []
        for ref in current_refs:
            formated_ref = format_ref_in_content(ref, papers, references_style)
            content = content.replace(
                f"[{ref}]", formated_ref
            )
            if formated_ref[1:-1] not in used_refs:
                used_refs.append(formated_ref[1:-1])
            if ref not in existing_refs:
                existing_refs.append(ref)
        content = content.replace(")(", "; ").replace(") (", "; ").replace("), (", "; ")
        matches = re.findall(r'\((.*?)\)', content)
        for match in matches:
            if ";" in match:
                refs = match.split(";")
                refs = list(set(refs))
                sort_refs = sorted([ref for ref in refs if ref in used_refs])
                content = content.replace(f'({match})', f"({"; ".join(sort_refs)})")
        content = re.sub(r'\[(?!\d+\])[^]]*\]', '', content)
    return content, existing_refs


def format_ref_in_content(title: str, papers: list[dict], references_style: str) -> str:
    result = next(paper for paper in papers if paper.get("title") == title)
    first_author = result["authors"][0].strip()
    if "." not in first_author:
        author_last_name = first_author.split(" ")[0]
    else:
        author_last_name = first_author.split(" ")[0] if "." not in first_author.split(" ")[0] else first_author.split(" ")[-1]
    if references_style == "APA":
        year = f", {result["year"]}" if result["year"] not in ["Unknown", "N/A", ""] else ""
        pages = ""
        return f"({author_last_name + year + pages})"
    elif references_style == "Chicago":
        year = f", {result["year"]}" if result["year"] not in ["Unknown", "N/A", ""] else ""
        publisher = f", {result["publisher"]}" if result["publisher"] not in ["Unknown", "N/A", ""] else ""
        pages = ""
        return f"({author_last_name + publisher + year + pages})"
    elif references_style == "ASA":
        year = f" {result["year"]}" if result["year"] not in ["Unknown", "N/A", ""] else ""
        pages = ""
        return f"({author_last_name + year + pages})"
    elif references_style == "MLA":
        pages = ""
        return f"({author_last_name + pages})"
    elif references_style == "Harvard":
        year = f", {result["year"]}" if result["year"] not in ["Unknown", "N/A", ""] else ""
        return f"({author_last_name + year})"
    else:
        return f"({author_last_name})"


def shorten_authors_name(authors: list[str]) -> str:
    shorten_names: str = ""
    for author in authors:
        if author:
            last_name = author.split(" ")[0]
            name = author.replace(last_name + " ", "")
            shorten_names += last_name + ", " + ". ".join([word[0] for word in name.split(" ")]) + "., "
    return shorten_names[:-2]


async def format_ref_in_ref_section(title: str, papers: list[dict], references_style: str):
    result = next(paper for paper in papers if paper.get("title") == title)
    authors = ", ".join([author.replace(" ", ", ", 1) for author in result["authors"]])
    shorten_authors = shorten_authors_name(result["authors"])
    if references_style == "APA":
        year = f" ({result["year"]})." if result["year"] not in ["Unknown", "N/A", ""] else ""
        journal = f" {result["journal"]}." if result["journal"] not in ["Unknown", "N/A", ""] else ""
        publisher = f" {result["publisher"]}" if result["publisher"] not in ["Unknown", "N/A", ""] else ""
        return f'{shorten_authors}{year} {title}.{publisher}' if publisher else f'{shorten_authors}{year} {title}.{journal}'
    elif references_style == "Chicago":
        year = f", {result["year"]}" if result["year"] not in ["Unknown", "N/A", ""] else ""
        journal = f". {result["journal"]}" if result["journal"] not in ["Unknown", "N/A", ""] else ""
        publisher = f". {result["publisher"]}" if result["publisher"] not in ["Unknown", "N/A", ""] else ""
        return f'{authors}. {title + publisher + year}.' if publisher else f'{authors}. {title + journal + year}.'
    elif references_style == "ASA":
        year = f". {result["year"]}" if result["year"] not in ["Unknown", "N/A", ""] else ""
        journal = f" *{result["journal"]}*" if result["journal"] not in ["Unknown", "N/A", ""] else ""
        vol = f" {result["volume"]}" if result["volume"] not in ["Unknown", "N/A", ""] else ""
        issue = f"({result["issue"]})" if result["issue"] not in ["Unknown", "N/A", ""] else ""
        pages = ""
        return f'{shorten_authors[:-1] + year}. "{title}"{journal + vol + issue + pages}.'
    elif references_style == "MLA":
        year = f", {result["year"]}." if result["year"] not in ["Unknown", "N/A", ""] else ""
        journal = f". {result["journal"]}" if result["journal"] not in ["Unknown", "N/A", ""] else ""
        publisher = f". {result["publisher"]}" if result["publisher"] not in ["Unknown", "N/A", ""] else ""
        return f'{authors}. {title + publisher + year}.' if publisher else f'{authors}. {title + journal + year}.'
    elif references_style == "CSE":
        year = f". {result["year"]}" if result["year"] not in ["Unknown", "N/A", ""] else ""
        journal = f". {result["journal"]}" if result["journal"] not in ["Unknown", "N/A", ""] else ""
        vol = f". {result["volume"]}" if result["volume"] not in ["Unknown", "N/A", ""] else ""
        issue = f"({result["issue"]})" if result["issue"] not in ["Unknown", "N/A", ""] else ""
        pages = ""
        return f'{shorten_authors[:-1] + year}. {title + journal + vol + issue + pages}.'
    elif references_style == "Vancouver":
        year = f". {result["year"]}" if result["year"] not in ["Unknown", "N/A", ""] else ""
        journal = f". {result["journal"]}" if result["journal"] not in ["Unknown", "N/A", ""] else ""
        vol = f"; {result["volume"]}" if result["volume"] not in ["Unknown", "N/A", ""] else ""
        issue = f"({result["issue"]})" if result["issue"] not in ["Unknown", "N/A", ""] else ""
        pages = ""
        return f'{shorten_authors[:-1]} {title + journal + year + vol + issue + pages}.'
    elif references_style == "IEEE":
        year = f", {result["year"]}" if result["year"] not in ["Unknown", "N/A", ""] else ""
        journal = f", {result["journal"]}" if result["journal"] not in ["Unknown", "N/A", ""] else ""
        publisher = f", {result["publisher"]}" if result["publisher"] not in ["Unknown", "N/A", ""] else ""
        return f'{shorten_authors[:-1]} {title + publisher + year}.' if publisher else f'{shorten_authors[:-1]} {title + journal + year}.'
    elif references_style == "Harvard":
        year = f" ({result["year"]})." if result["year"] not in ["Unknown", "N/A", ""] else ""
        journal = f". {result["journal"]}" if result["journal"] not in ["Unknown", "N/A", ""] else ""
        publisher = f". {result["publisher"]}" if result["publisher"] not in ["Unknown", "N/A", ""] else ""
        return f'{shorten_authors[:-1] + year} {title + publisher}.' if publisher else f'{shorten_authors[:-1] + year} {title + journal}.'
    else:
        year = f". {result["year"]}." if result["year"] not in ["Unknown", "N/A", ""] else ""
        journal = f". {result["journal"]}" if result["journal"] not in ["Unknown", "N/A", ""] else ""
        return f'{shorten_authors[:-1] + year} {title + journal}.'