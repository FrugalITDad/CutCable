#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
CutCable Build Wizard - Background Service for Automatic Updates
"""

import xbmc
import time
import sys
import os

# Add the current directory to Python path
addon_dir = os.path.dirname(__file__)
sys.path.insert(0, addon_dir)

from cutcable_wizard import CutCableWizard

class CutCableService:
    def __init__(self):
        self.wizard = CutCableWizard()
        self.monitor = xbmc.Monitor()
        
    def run(self):
        """Main service loop"""
        xbmc.log('CutCable Service: Started', xbmc.LOGINFO)
        
        # Wait for Kodi to fully start up
        startup_delay = 30  # seconds
        if self.monitor.waitForAbort(startup_delay):
            return
        
        # Perform startup update check
        try:
            self.wizard.startup_update_check()
        except Exception as e:
            xbmc.log(f'CutCable Service: Startup check failed - {str(e)}', xbmc.LOGERROR)
        
        # Keep service running but dormant
        # The main update checking is done on startup only
        while not self.monitor.abortRequested():
            # Check every hour if service should continue
            if self.monitor.waitForAbort(3600):  # 1 hour
                break
        
        xbmc.log('CutCable Service: Stopped', xbmc.LOGINFO)

if __name__ == '__main__':
    service = CutCableService()
    service.run()
