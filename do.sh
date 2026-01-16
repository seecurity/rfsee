#!/bin/bash

rm -f compile.sh
python3 rfsee.py
parallel --progress < compile.sh 
open dot/RFC4880.html
