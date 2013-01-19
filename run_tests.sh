#!/bin/sh

cd tests
for NAME in test_*.py; do
  echo "[Executing] $NAME"
  python $NAME
done
