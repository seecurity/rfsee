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
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>RFSee RFC Browser</title>

  <style>
    body {
      font-family: sans-serif;
      max-width: 700px;
      margin: 2rem auto;
      line-height: 1.6;
    }

    input {
      width: 100%;
      padding: 0.5rem;
      font-size: 1rem;
    }

    ul {
      margin: 0.5rem 0 1.5rem;
      padding-left: 1.2rem;
    }

    li {
      margin: 0.25rem 0;
    }

    .jump-highlight {
      outline: 3px solid #007acc;
      outline-offset: 4px;
    }

    hr {
      margin: 3rem 0;
    }
  </style>
</head>
<body>

  <h1>RFSee RFC Browser</h1>

  <p>
    Search for RFC numbers, names or years below and press Enter
    or click a result.
  </p>

  <!-- Search UI -->
  <input id="search" placeholder="Search sections…" autocomplete="off" />
  <ul id="results"></ul>

  <hr>
""")

    for rfc in RFC_INFO.keys():
        title = RFC_INFO[rfc][0].replace("\n", " ")
        f.write("""
<h4 id="%s">%s</h4>
<p><a href="%s.html" data-tile="%s">%s -- %s</a></p>\n""" % (rfc, rfc + " -- " + title, rfc, rfc + " -- " + title, rfc, title))

    f.write("""  <!-- JavaScript -->
  <script>
  (() => {
    const input = document.getElementById("search");
    const results = document.getElementById("results");

    // Collect headings with IDs
    const candidates = [];
    document
      .querySelectorAll("h1[id],h2[id],h3[id],h4[id],h5[id],h6[id]")
      .forEach(h => {
        candidates.push({
          id: h.id,
          label: h.textContent.trim(),
          el: h
        });
      });

    function clearResults() {
      results.innerHTML = "";
    }

    function highlightAndScroll(el, id) {
      history.pushState(null, "", "#" + encodeURIComponent(id));
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      el.classList.add("jump-highlight");
      setTimeout(() => el.classList.remove("jump-highlight"), 1200);
    }

    function render(matches) {
      clearResults();
      for (const m of matches.slice(0, 15)) {
        const li = document.createElement("li");
        const link = document.createElement("a");
        link.href = "#" + encodeURIComponent(m.id);
        link.textContent = m.label;
        link.addEventListener("click", (e) => {
          e.preventDefault();
          highlightAndScroll(m.el, m.id);
          clearResults();
        });
        li.appendChild(link);
        results.appendChild(li);
      }
    }

    function search(q) {
      q = q.trim().toLowerCase();
      if (!q) {
        clearResults();
        return;
      }

      const matches = candidates
        .map(c => {
          const hay = (c.label + " " + c.id).toLowerCase();
          const idx = hay.indexOf(q);
          return { ...c, score: idx === -1 ? Infinity : idx };
        })
        .filter(x => x.score !== Infinity)
        .sort((a, b) => a.score - b.score || a.label.length - b.label.length);

      render(matches);
    }

    input.addEventListener("input", () => search(input.value));

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const first = results.querySelector("a");
        if (first) first.click();
      } else if (e.key === "Escape") {
        clearResults();
        input.blur();
      }
    });
  })();
  </script>

</body>
</html> """)
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

if __name__ == "__main__":
    main(RFC_INDEX_XML)
