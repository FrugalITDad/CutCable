#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
CutCable Build Wizard - Main Entry Point
"""

import sys
import os

# Add the current directory to Python path
addon_dir = os.path.dirname(__file__)
sys.path.insert(0, addon_dir)

# Import and run the wizard
from cutcable_wizard import CutCableWizard

if __name__ == '__main__':
    wizard = CutCableWizard()
    wizard.show_main_menu()
