from aqt.editor import Editor
from bs4 import BeautifulSoup
import os
import requests

current_path = os.path.dirname(__file__)

import sys
sys.path.append(current_path)

try:
    from lxml import etree
except ImportError:
    from PyQt5.QtWidgets import QWidget, QMessageBox
    from PyQt5.QtCore import Qt
    message_box = QMessageBox()
    message_box.setTextInteractionFlags(Qt.TextSelectableByMouse)
    message_box.setText(f"lxml not found. Please run \npip install lxml -t {current_path}\notherwise MathJax parsing will not work.")
    message_box.show()
    print("lxml not found")


def _parse_math_from_mathjax(self, doc: BeautifulSoup):

    try:
        from lxml import etree
    except ImportError:
        return

    mathjax_elements = doc.find_all(None, {"class": "MathJax"})

    if not mathjax_elements:
        return

    xslt_file = os.path.join(current_path, "mmltex.xsl")
    if not os.path.exists(xslt_file):
        # Download XML transformation rules to convert MathML into LaTeX:
        filelist = ["cmarkup.xsl", "entities.xsl", "glayout.xsl",
                    "mmltex.xsl", "scripts.xsl", "tables.xsl", "tokens.xsl"]
        for filename in filelist:
            r = requests.get(f"https://raw.githubusercontent.com/oerpub/mathconverter/master/xsl_yarosh/{filename}")
            with open(os.path.join(current_path, filename), "wb") as f:
                f.write(r.content)

    xslt = etree.parse(xslt_file)

    for tag in mathjax_elements:
        if 'data-mathml' not in tag.attrs:
            continue
        mathml_string = tag.attrs['data-mathml']
        dom = etree.fromstring(mathml_string)
        transform = etree.XSLT(xslt)
        newdom = transform(dom)
        latex_string = str(newdom).replace("\n", " ").replace("\t", " ").strip()
        if latex_string.startswith("$$"):
            latex_string = f"\\[{latex_string.replace('$$', '')}\\]"
        elif latex_string.startswith("$"):
            latex_string = f"\\({latex_string.replace('$', '')}\\)"
        tag.clear()
        tag.string = latex_string


def _parse_math_from_wikipedia(self, doc: BeautifulSoup):
    spans = doc.find_all("span", attrs={"class": "mwe-math-element"})
    for span in spans:
        math = span.find("img")
        if math is None:
            continue
        latex_string = math.attrs.get("alt", "")
        latex_string = f"\\({latex_string}\\)"
        span.clear()
        span.string = latex_string


def _pastePreFilter(self, html: str, internal: bool) -> str:
    # This function will be monkey-patched and overwrite Editor._pastePreFilter

    doc = BeautifulSoup(html, "html.parser")

    # Add the calls to transform the detected mathematical formulae inside the HTML content:
    self._parse_math_from_mathjax(doc)
    self._parse_math_from_wikipedia(doc)

    html = str(doc)

    # Call the previous Editor._pastePreFilter (now renamed _pastePreFilterPrevVers)
    # in order to complete the parsing of the HTML:
    return self._pastePreFilterPrevVers(html, internal)


Editor._pastePreFilterPrevVers = Editor._pastePreFilter
Editor._pastePreFilter = _pastePreFilter
Editor._parse_math_from_wikipedia = _parse_math_from_wikipedia
Editor._parse_math_from_mathjax = _parse_math_from_mathjax
