#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
CutCable Build Wizard - Main Entry Point
"""

import sys
import os
import xbmc

# Add the current directory to Python path
addon_dir = os.path.dirname(__file__)
sys.path.insert(0, addon_dir)

# Kodi log to indicate script start
xbmc.log("CutCable Wizard: Starting wizard entry point.", level=xbmc.LOGNOTICE)

try:
    # Import and run the wizard
    from cutcable_wizard import CutCableWizard

    if __name__ == '__main__':
        wizard = CutCableWizard()
        wizard.show_main_menu()

except Exception as e:
    xbmc.log(f"CutCable Wizard: Error occurred - {str(e)}", level=xbmc.LOGERROR)
