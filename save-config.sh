#!/bin/bash

rsync -vr --exclude=.git --exclude=*.sh . ~/
