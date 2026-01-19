#!/usr/bin/env python3
import sys
import xml.etree.ElementTree as ET
import re
from typing import List
import textwrap

TITLE_WIDTH = 40
RFC_INDEX_XML = "zips/xml/rfc-index.xml"
OUT_DIR = "dot/"
NS = {"r": "https://www.rfc-editor.org/rfc-index"}
RFC_INFO = {}

# Bracket blocks that contain RFC followed by optional whitespace and digits
_BRACKET_WITH_RFC = re.compile(
    r"\[(?=[^\]]*\bRFC\s*\d)([^\]]+)\]",
    re.IGNORECASE
)

# RFC token extractor: RFC + optional whitespace + 1..4 digits
_RFC_TOKEN = re.compile(r"\bRFC\s*(\d{1,4})\b", re.IGNORECASE)


def get_field_text(elem, field_name) -> str | None:
    node = elem.find(field_name, NS)
    if node is None:
        return None

    # Grab all descendant text, including <p>...</p>
    text = "".join(node.itertext()).strip()
    return text or None

def get_field(elem, field_name) -> str:
    doc = elem.find(field_name, NS)
    if doc is not None and doc.text:
        return doc.text.strip()

def get_sub_fields(elem, field_name) -> []:
    sub_field = elem.find(field_name, NS)
    ids = []
    if sub_field is not None:
        for d in sub_field.findall("r:doc-id", NS):
            if d.text:
                ids.append(d.text.strip())
    return ids

def write_index_html():
    f = open("dot/index.html", "w")

    # Write header
    with open("templates/index_head.html", "r", encoding="utf-8") as h:
        f.write(h.read())

    for rfc in RFC_INFO.keys():
        title = RFC_INFO[rfc][0].replace("\n", " ")
        f.write("""
<h4 id="%s">%s</h4>
<p><a href="%s.html" data-tile="%s">%s -- %s</a></p>\n""" % (rfc, rfc + " -- " + title, rfc, rfc + " -- " + title, rfc, title))

    # Write footer
    with open("templates/index_footer.html", "r", encoding="utf-8") as h:
        f.write(h.read())

    f.close()

def write_dot_src(rfc, month, year, obs_ids, obs_by_ids, updates, updated_by):
    f = open(OUT_DIR + "%s.dot" % rfc, "w")
    
    # Write file header
    f.write("""digraph Flow {
  layout=twopi;
  root=%s;
  overlap=false;
  %s [label="%s", shape=ellipse, fillcolor="#e8f0ff", tooltip="%s", style=filled, fillcolor=green, fontsize=18, penwidth=3, fontweight=bold]; 

""" % (rfc, rfc, rfc + "\n" + RFC_INFO[rfc][0], RFC_INFO[rfc][1]))

    # Write obsoleted by
    f.write("""  obs_by [label="obsoletes", shape=box, style=filled, fillcolor=lightblue];
  obs_by -> %s;\n""" % (rfc))
    for temp in obs_by_ids:
        if temp not in RFC_INFO.keys():
            RFC_INFO[temp] = ("", "")
        f.write("""  %s [label="%s", shape=ellipse, URL="%s.html", target="_top", tooltip="%s"];\n""" % (temp, temp + "\n" + RFC_INFO[temp][0], temp, RFC_INFO[temp][1]))
        f.write("""  %s -> obs_by;\n""" % (temp))

    # Write obsoletes 
    f.write("""\n  obs [label="obsoletes", shape=box, style=filled, fillcolor=lightblue];
  %s -> obs;\n""" % (rfc))
    for temp in obs_ids:
        if temp not in RFC_INFO.keys():
            RFC_INFO[temp] = ("", "")
        f.write("""  %s [label="%s", shape=ellipse, URL="%s.html", target="_top", tooltip="%s"];\n""" % (temp, temp + "\n" + RFC_INFO[temp][0], temp, RFC_INFO[temp][1]))
        f.write("""  obs -> %s;\n""" % (temp))

    # Write updates 
    f.write("""\n  updates [label="updates", shape=box, style=filled, fillcolor=lightyellow];
  %s -> updates;\n""" % (rfc))
    for temp in updates:
        if temp not in RFC_INFO.keys():
            RFC_INFO[temp] = ("", "")
        f.write("""  %s [label="%s", shape=ellipse, URL="%s.html", target="_top", tooltip="%s"];\n""" % (temp, temp + "\n" + RFC_INFO[temp][0], temp, RFC_INFO[temp][1]))
        f.write("""  updates -> %s;\n""" % (temp))

    # Write updated_by 
    f.write("""\n  updated_by [label="updates", shape=box, style=filled, fillcolor=lightyellow];
  updated_by -> %s;\n""" % (rfc))
    for temp in updated_by:
        if temp not in RFC_INFO.keys():
            RFC_INFO[temp] = ("", "")
        f.write("""  %s [label="%s", shape=ellipse, URL="%s.html", target="_top", tooltip="%s"];\n""" % (temp, temp + "\n" + RFC_INFO[temp][0], temp, RFC_INFO[temp][1]))
        f.write("""  %s -> updated_by;\n""" % (temp))

    # Write citations
    f.write("""\n  cites [label="cites", shape=box, style=filled, fillcolor=lightblue];
  %s -> cites;\n""" % (rfc))
    for citation in RFC_INFO[rfc][2]:
        if citation in RFC_INFO.keys():
            f.write("""  %s [label="%s", shape=ellipse, URL="%s.html", target="_top", tooltip="%s"];\n""" % (citation, citation + "\n" + RFC_INFO[citation][0], citation, RFC_INFO[citation][1]))
            f.write("""  cites -> %s;\n""" % (citation))

    # Write reverse citations
    f.write("""\n  rev_cites [label="cites", shape=box, style=filled, fillcolor=lightblue];
  rev_cites -> %s;\n""" % (rfc))
    for citation in RFC_INFO[rfc][3]:
        if citation in RFC_INFO.keys():
            f.write("""  %s [label="%s", shape=ellipse, URL="%s.html", target="_top", tooltip="%s"];\n""" % (citation, citation + "\n" + RFC_INFO[citation][0], citation, RFC_INFO[citation][1]))
            f.write("""  %s -> rev_cites;\n""" % (citation))


    f.write("}\n")
    f.close()
    
def write_html(rfc):
    f = open(OUT_DIR + "%s.html" % rfc, "w")
    f.write("""<!doctype html><meta charset="utf-8"><title>RFSee</title><body>
  <style>
    body {
      margin: 20px;
      font-family: Arial, sans-serif;
    }

    object {
      width: 100%s;
      height: auto;
      display: block;
    }
  </style>
<h3>RFSee (click nodes)</h3>
<p><a href="index.html">Got back to RFSee search.</a></p>
<object type="image/svg+xml" data="%s.svg"></object>
</body> """ % ("%", rfc))
    f.close()

def write_compile_dot(rfc):
    f = open("compile.sh", "a")
    f.write("""dot -Tsvg -o %s.svg %s.dot\n""" % (OUT_DIR + rfc, OUT_DIR + rfc))
    f.close()

def prep_hashtable(path: str) -> None:
    # Stream parse; process elements when their closing tag is reached
    for event, elem in ET.iterparse(path, events=("end",)):
        if elem.tag == f"{{{NS['r']}}}rfc-entry":
            rfc = get_field(elem, "r:doc-id")
            title = str(get_field(elem, "r:title")).replace("\"", "")
            title = "\n".join(textwrap.wrap(title, width=TITLE_WIDTH))
            date = elem.find("r:date", NS)
            month = get_field(date, "r:month")
            year = get_field(date, "r:year")
            abstract = str(get_field_text(elem, "r:abstract")).replace("\"", "")
            citations = get_citations(rfc)
            rev_cites = []
            RFC_INFO[rfc] = (title + "\n" + year, abstract, citations, rev_cites)

    # now do "reverse" citations
    # durch alle RFCs von vorn nach hinten
    for rfc in RFC_INFO.keys():
        citations = RFC_INFO[rfc][2]
        # auf welche anderen RFCs verlinkt dieser RFC?
        for cite in citations:
            if cite in RFC_INFO.keys():
                # Hole die bisher bekannten verlinkungen
                rev_cites = RFC_INFO[cite][3]
                if cite not in rev_cites:
                    rev_cites.append(rfc)
                    RFC_INFO[cite] = (RFC_INFO[cite][0], RFC_INFO[cite][1], RFC_INFO[cite][2], rev_cites)
    

def get_citations(rfc: str) -> List[str]:
    while rfc[3] == "0":
        rfc = "rfc" + rfc[4:]
    raw = ""
    try:
        f = open("zips/%s.txt" % rfc.lower(), "r")
        raw = f.read()
        f.close()
        return extract_rfc_citations(raw, rfc)
    except:
        print("Could not open %s" % rfc.lower())
        return []

def extract_rfc_citations_with_counts(text: str) -> List[tuple[str, int]]:
    """
    Extract RFC citations from bracketed references and count how often each RFC
    is cited.

    Examples handled:
      [RFC1234]
      [RFC 1234]
      [RFC1234, RFC2345, rfc 3456]

    Returns:
      [('RFC1234', 4), ('RFC2345', 1), ('RFC3456', 3)]
    Order is first appearance in the text.
    """
    counts = OrderedDict()

    for m in _BRACKET_WITH_RFC.finditer(text):
        inside = m.group(1)
        for num in _RFC_TOKEN.findall(inside):
            rfc = f"RFC{int(num)}"  # normalize case & leading zeros
            counts[rfc] = counts.get(rfc, 0) + 1

    return list(counts.items())


def extract_rfc_citations(text: str, rfc: str) -> List[str]:
    """
    Extract RFC citations only from bracketed blocks like:
      [RFC1234], [RFC 1234], [RFC1234, RFC2345, rfc 3456]
    Returns de-duplicated list in order of appearance: ["RFC1234", ...]
    """
    results: List[str] = []
    seen = set()
    seen.add(rfc)

    for m in _BRACKET_WITH_RFC.finditer(text):
        inside = m.group(1)
        for num in _RFC_TOKEN.findall(inside):
            token = f"RFC{int(num)}"  # normalizes e.g. RFC0007 -> RFC7
            if token not in seen:
                seen.add(token)
                results.append(token)

    return results

def calc_toplist():
    f = open("dot/top_refed_by.html", "w")
    
    with open("templates/top_refed_by_header.html", "r", encoding="utf-8") as h:
        f.write(h.read())
    
    ar = []
    for rfc in RFC_INFO.keys():
        if len(RFC_INFO[rfc]) != 4:
            continue
        #print("%d times cited: %s" % (len(RFC_INFO[rfc][3]), rfc))
        ar.append("""<tr><td><a href="%s.html">%s</a></td><td>%s</td><td>%s</td></tr>\n""" % (rfc, rfc, RFC_INFO[rfc][0], len(RFC_INFO[rfc][3])))

    ar.sort(reverse=True)
    f.write("\n".join(ar))

    with open("templates/top_refed_by_footer.html", "r", encoding="utf-8") as h:
        f.write(h.read())

    f.close()
        

def main(path: str) -> None:
    prep_hashtable(path)
    write_index_html()
    # Stream parse; process elements when their closing tag is reached
    for event, elem in ET.iterparse(path, events=("end",)):
        if elem.tag == f"{{{NS['r']}}}rfc-entry":
            #doc = elem.find("r:doc-id", NS)
            #if doc is not None and doc.text:
            #    print(doc.text.strip())
            rfc = get_field(elem, "r:doc-id")
            date = elem.find("r:date", NS)
            month = get_field(date, "r:month")
            year = get_field(date, "r:year")
            obs_ids = get_sub_fields(elem, "r:obsoletes")
            obs_by_ids = get_sub_fields(elem, "r:obsoleted-by")
            updates = get_sub_fields(elem, "r:updates")
            updated_by = get_sub_fields(elem, "r:updated-by")

            write_dot_src(rfc, month, year, obs_ids, obs_by_ids, updates, updated_by)
            write_html(rfc)
            write_compile_dot(rfc)

            print("rfc: " + rfc + ", year: " + str(year) + "-" + month + ", obsoletes: " + str(obs_ids) + ", obsoleted-by: " + str(obs_by_ids) + ", updates: " + str(updates) + ", updated-by: " + str(updated_by))

            # free memory for this subtree
            elem.clear()
            date.clear()
    calc_toplist()

if __name__ == "__main__":
    main(RFC_INDEX_XML)
