import os
import sys

basedir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, basedir + '/../')

from minitwit import minitwit
from utils import logging
