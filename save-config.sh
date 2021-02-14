#!/bin/bash

rsync -avr --exclude=.git* --exclude=*.sh . ~/
