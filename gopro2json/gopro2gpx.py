#!/usr/bin/env python
#
# 17/02/2019 
# Juan M. Casillas <juanm.casillas@gmail.com>
# https://github.com/juanmcasillas/gopro2gpx.git
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
#


import subprocess
import re
import struct
import os
import math
import platform
import argparse
from collections import namedtuple
import array
import sys
import time
from datetime import datetime

import config
import gpmf
import fourCC
import time
import sys

import json

def Build360Points(data, skip=False):
    """
    Data comes UNSCALED so we have to do: Data / Scale.
    Do a finite state machine to process the labels.
    GET
     - SCAL     Scale value
    """

    SCAL = fourCC.XYZData(1.0, 1.0, 1.0)
    DVID = None
    TSMP = None
    GPSU = None
    VPTS = None
    VPTS_init = None
    CTS = 0
    SYST = fourCC.SYSTData(0, 0)

    DATAS = ['CORI', 'IORI', 'GRAV']
    samples = []
    streams = { 'streams': {
        'datas': DATAS,
        'samples': samples
    }}

    stats = { 
        'ok': 0,
        'badfix': 0,
        'badfixskip': 0,
        'empty' : 0
    }

    GPSFIX = 0 # no lock.
    for d in data:
        if d.fourCC == 'SCAL':
            SCAL = d.data
        elif d.fourCC == 'TSMP':
            TSMP = d.data
        elif d.fourCC == 'VPTS':
            if VPTS == None:
                VPTS_init = d.data
            VPTS = d.data
            CTS = int((VPTS - VPTS_init) / 1000)
        elif d.fourCC in DATAS:
            sample = { 'CTS': CTS, 'VPTS': VPTS, 'SCAL': SCAL } if len(samples) == 0 else samples[-1]
            if sample['CTS'] < CTS:
                sample = { 'CTS': CTS, 'VPTS': VPTS, 'SCAL': SCAL }

            sample[d.fourCC] = dict(zip(['w', 'x', 'z', 'y'], d.data))
            
            if len(samples) == 0 or samples[-1]['CTS'] < CTS:
                samples.append(sample)

    streams['streams']['FPS'] = round(1 / ((VPTS - VPTS_init) / 1000000 / len(samples)), 3)
    return streams

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="count")
    parser.add_argument("-b", "--binary", help="read data from bin file", action="store_true")
    parser.add_argument("-s", "--skip", help="Skip bad points (GPSFIX=0)", action="store_true", default=False)
    parser.add_argument("file", help="Video file or binary metadata dump")
    args = parser.parse_args()

    return args        

if __name__ == "__main__":

    args = parseArgs()
    config = config.setup_environment(args)
    parser = gpmf.Parser(config)

    if not args.binary:
        data = parser.readFromMP4()
    else:
        data = parser.readFromBinary()

    CASN = parser.readCameraSerial()

    streams = Build360Points(data, skip=args.skip)

    if len(streams) == 0:
        print("Can't create file. No camera info in %s. Exitting" % config.file)
        sys.exit(0)

    streams['camera'] = CASN
    streams['source'] = config.outputfile
    streams['date'] = parser.date

    #
    # Write the results
    #
    fd = open("%s.json" % config.outputfile , "w+")
    fd.write(json.dumps(streams))
    fd.close()
