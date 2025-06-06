#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
CutCable Wizard - Main Entry Point
Fire TV optimized entry point with error handling
"""

import sys
import os
import xbmc

# Add the current directory to Python path
addon_dir = os.path.dirname(__file__)
sys.path.insert(0, addon_dir)

# Kodi log to indicate script start
xbmc.log("CutCable Wizard: Starting wizard entry point", xbmc.LOGINFO)

try:
    # Import and run the wizard
    from cutcable_wizard import CutCableWizard
    
    if __name__ == '__main__':
        # Fire TV optimization - ensure clean start
        import gc
        gc.collect()
        
        wizard = CutCableWizard()
        wizard.show_main_menu()
        
        # Clean up after wizard closes
        del wizard
        gc.collect()
        
        xbmc.log("CutCable Wizard: Wizard session completed", xbmc.LOGINFO)
        
except Exception as e:
    xbmc.log(f"CutCable Wizard: Critical error occurred - {str(e)}", xbmc.LOGERROR)
    
    # Try to show error to user if possible
    try:
        import xbmcgui
        xbmcgui.Dialog().ok("CutCable Wizard Error", 
                           f"An error occurred starting the wizard:\n{str(e)}\n\nPlease check the Kodi log for details.")
    except:
        pass
