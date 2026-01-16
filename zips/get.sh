#!/bin/bash

rm -rf RFC-all.tar.gz xml a

wget https://www.rfc-editor.org/in-notes/tar/RFC-all.tar.gz
tar xzvf RFC-all.tar.gz
rm -f *.json *.html *.ps *.pdf

mkdir xml
cd xml
wget https://www.rfc-editor.org/rfc/rfc-index.xml

