#!/bin/bash

mkdir -p build
cd build
time cmake ..
time make
cd ..
