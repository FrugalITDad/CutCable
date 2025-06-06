#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
CutCable Build Wizard - Background Service for Automatic Updates
"""

import xbmc
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
        xbmc.log('CutCable Service: Started', xbmc.LOGNOTICE)
        
        # Wait for Kodi to fully start up (30 seconds)
        startup_delay = 30
        if self.monitor.waitForAbort(startup_delay):
            xbmc.log('CutCable Service: Aborted during startup delay', xbmc.LOGNOTICE)
            return
        
        # Perform startup update check
        try:
            xbmc.log('CutCable Service: Performing startup update check', xbmc.LOGDEBUG)
            self.wizard.startup_update_check()
        except Exception as e:
            xbmc.log(f'CutCable Service: Startup check failed - {str(e)}', xbmc.LOGERROR)
        
        # Periodic daily check loop
        daily_check_seconds = 86400  # 24 hours
        
        while not self.monitor.abortRequested():
            # Wait up to 24 hours or until Kodi requests abort
            if self.monitor.waitForAbort(daily_check_seconds):
                # Abort requested during wait
                xbmc.log('CutCable Service: Abort requested, exiting service loop', xbmc.LOGNOTICE)
                break
            
            # Perform periodic update check
            try:
                xbmc.log('CutCable Service: Performing periodic update check', xbmc.LOGDEBUG)
                self.wizard.periodic_update_check()
            except Exception as e:
                xbmc.log(f'CutCable Service: Periodic update check failed - {str(e)}', xbmc.LOGERROR)
        
        # Optional cleanup before exit
        try:
            if hasattr(self.wizard, 'cleanup'):
                xbmc.log('CutCable Service: Performing cleanup', xbmc.LOGDEBUG)
                self.wizard.cleanup()
        except Exception as e:
            xbmc.log(f'CutCable Service: Cleanup failed - {str(e)}', xbmc.LOGERROR)
        
        xbmc.log('CutCable Service: Stopped', xbmc.LOGNOTICE)

if __name__ == '__main__':
    service = CutCableService()
    service.run()
