#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML解析器模块
"""

import sys
import os

sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

from .base_parser import BaseParser
from .alibaba_parser import AlibabaParser
from .jd_parser import JDParser
from .factory import ParserFactory

__all__ = ['BaseParser', 'AlibabaParser', 'JDParser', 'ParserFactory']
