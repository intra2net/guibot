#!/bin/sh

cd tests
for NAME in test_*.py; do
  python $NAME
done
