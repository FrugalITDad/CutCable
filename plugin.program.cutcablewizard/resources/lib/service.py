#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
CutCable Wizard - Background Service
Handles startup tasks, update checks, and maintenance operations
"""

import os
import sys
import time
import threading
import gc
import json
import xbmc
import xbmcaddon
import xbmcvfs

# Import the main wizard class
try:
    from cutcable_wizard import CutCableWizard
except ImportError:
    # Handle path issues for imports
    addon_path = xbmcaddon.Addon().getAddonInfo('path')
    sys.path.insert(0, addon_path)
    from cutcable_wizard import CutCableWizard

class CutCableWizardService:
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.addon_id = self.addon.getAddonInfo('id')
        self.addon_version = self.addon.getAddonInfo('version')
        self.addon_path = self.addon.getAddonInfo('path')
        
        # Service control flags
        self.monitor = xbmc.Monitor()
        self.running = True
        self.startup_complete = False
        
        # Initialize wizard instance
        self.wizard = None
        
        # Service intervals (in seconds)
        self.startup_delay = 10  # Delay before startup tasks
        self.update_check_interval = 3600  # 1 hour between update checks
        self.maintenance_interval = 86400  # 24 hours between maintenance tasks
        self.memory_cleanup_interval = 1800  # 30 minutes between memory cleanup
        
        # Last execution timestamps
        self.last_update_check = 0
        self.last_maintenance = 0
        self.last_memory_cleanup = 0
        
        xbmc.log(f"CutCable Wizard Service: Initializing service v{self.addon_version}", xbmc.LOGINFO)

    def initialize_wizard(self):
        """Initialize the wizard instance with error handling"""
        try:
            if not self.wizard:
                self.wizard = CutCableWizard()
                xbmc.log("CutCable Wizard Service: Wizard instance initialized", xbmc.LOGDEBUG)
                return True
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error initializing wizard - {str(e)}", xbmc.LOGERROR)
            return False
        return True

    def startup_tasks(self):
        """Perform startup tasks after Kodi fully loads"""
        try:
            xbmc.log("CutCable Wizard Service: Starting startup tasks", xbmc.LOGINFO)
            
            # Wait for Kodi to fully load
            self.wait_for_kodi_ready()
            
            # Initialize wizard
            if not self.initialize_wizard():
                return
            
            # Check for pending installation completion
            self.check_pending_installation()
            
            # Perform startup update check if enabled
            if hasattr(self.wizard, 'settings') and self.wizard.settings.get('auto_updates', True):
                self.startup_update_check()
            
            # Clean up old temporary files
            self.cleanup_temp_files()
            
            # Check system health
            self.system_health_check()
            
            self.startup_complete = True
            xbmc.log("CutCable Wizard Service: Startup tasks completed", xbmc.LOGINFO)
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error in startup tasks - {str(e)}", xbmc.LOGERROR)

    def wait_for_kodi_ready(self):
        """Wait for Kodi to be fully ready"""
        max_wait = 60  # Maximum wait time in seconds
        wait_time = 0
        
        while wait_time < max_wait and not self.monitor.abortRequested():
            if xbmc.getCondVisibility('System.HasAddon(skin.confluence)') or \
               xbmc.getCondVisibility('System.HasAddon(skin.estuary)') or \
               len(xbmc.getInfoLabel('System.BuildVersion')) > 0:
                break
            
            self.monitor.waitForAbort(1)
            wait_time += 1
        
        # Additional small delay to ensure everything is loaded
        self.monitor.waitForAbort(2)

    def check_pending_installation(self):
        """Check for pending build installation completion"""
        try:
            if not self.wizard:
                return
            
            # Check if wizard has addon_data_path attribute
            if hasattr(self.wizard, 'addon_data_path'):
                marker_file = os.path.join(self.wizard.addon_data_path, 'install_marker.json')
                if xbmcvfs.exists(marker_file):
                    xbmc.log("CutCable Wizard Service: Found pending installation, completing...", xbmc.LOGINFO)
                    
                    # Complete the installation if method exists
                    if hasattr(self.wizard, 'complete_installation'):
                        self.wizard.complete_installation()
                    
                    # Show completion notification after a delay
                    threading.Timer(5.0, self.show_completion_notification).start()
                
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error checking pending installation - {str(e)}", xbmc.LOGERROR)

    def show_completion_notification(self):
        """Show installation completion notification"""
        try:
            if self.wizard and hasattr(self.wizard, 'build_info') and self.wizard.build_info.get('installed_build'):
                build_name = self.wizard.build_info['installed_build']
                xbmc.executebuiltin(f'Notification(CutCable Wizard, {build_name} installation complete!, 8000)')
        except:
            pass

    def startup_update_check(self):
        """Perform startup update check in background"""
        def update_check_thread():
            try:
                # Small delay to not interfere with startup
                time.sleep(5)
                
                if not self.monitor.abortRequested() and self.wizard:
                    if hasattr(self.wizard, 'startup_update_check'):
                        self.wizard.startup_update_check()
                    self.last_update_check = time.time()
                    
            except Exception as e:
                xbmc.log(f"CutCable Wizard Service: Error in startup update check - {str(e)}", xbmc.LOGERROR)
        
        # Run in background thread
        update_thread = threading.Thread(target=update_check_thread)
        update_thread.daemon = True
        update_thread.start()

    def cleanup_temp_files(self):
        """Clean up temporary files from previous sessions"""
        try:
            if not self.wizard or not hasattr(self.wizard, 'temp_path'):
                return
            
            temp_path = self.wizard.temp_path
            if not os.path.exists(temp_path):
                return
            
            cleaned_count = 0
            for item in os.listdir(temp_path):
                if item.startswith(('build_', 'extract_')):
                    item_path = os.path.join(temp_path, item)
                    try:
                        if os.path.isdir(item_path):
                            import shutil
                            shutil.rmtree(item_path, ignore_errors=True)
                        else:
                            os.remove(item_path)
                        cleaned_count += 1
                    except:
                        pass
            
            if cleaned_count > 0:
                xbmc.log(f"CutCable Wizard Service: Cleaned {cleaned_count} temporary files", xbmc.LOGDEBUG)
                
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error cleaning temp files - {str(e)}", xbmc.LOGERROR)

    def system_health_check(self):
        """Perform basic system health checks"""
        try:
            # Check available disk space
            self.check_disk_space()
            
            # Check for corrupt databases
            self.check_database_health()
            
            # Verify critical directories exist
            self.verify_directories()
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error in system health check - {str(e)}", xbmc.LOGERROR)

    def check_disk_space(self):
        """Check available disk space and warn if low"""
        try:
            userdata_path = xbmcvfs.translatePath('special://userdata/')
            
            # Get disk usage using statvfs if available
            if hasattr(os, 'statvfs'):
                statvfs = os.statvfs(userdata_path)
                free_space = statvfs.f_frsize * statvfs.f_bavail
                total_space = statvfs.f_frsize * statvfs.f_blocks
                
                # Convert to MB
                free_mb = free_space // (1024 * 1024)
                total_mb = total_space // (1024 * 1024)
                
                # Warn if less than 500MB free
                if free_mb < 500:
                    xbmc.log(f"CutCable Wizard Service: Low disk space warning - {free_mb}MB free", xbmc.LOGWARNING)
                    xbmc.executebuiltin(f'Notification(CutCable Wizard, Low disk space: {free_mb}MB free, 10000)')
                
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error checking disk space - {str(e)}", xbmc.LOGERROR)

    def check_database_health(self):
        """Basic database health check"""
        try:
            database_path = xbmcvfs.translatePath('special://userdata/Database/')
            if not os.path.exists(database_path):
                return
            
            # Check for database files
            db_files = []
            for file in os.listdir(database_path):
                if file.endswith('.db'):
                    db_files.append(file)
            
            if not db_files:
                xbmc.log("CutCable Wizard Service: No database files found", xbmc.LOGWARNING)
            else:
                xbmc.log(f"CutCable Wizard Service: Found {len(db_files)} database files", xbmc.LOGDEBUG)
                
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error checking database health - {str(e)}", xbmc.LOGERROR)

    def verify_directories(self):
        """Verify critical directories exist"""
        try:
            critical_dirs = [
                'special://userdata/',
                'special://userdata/addon_data/',
                'special://userdata/Database/',
                'special://temp/'
            ]
            
            for dir_special in critical_dirs:
                dir_path = xbmcvfs.translatePath(dir_special)
                if not xbmcvfs.exists(dir_path):
                    xbmcvfs.mkdirs(dir_path)
                    xbmc.log(f"CutCable Wizard Service: Created missing directory - {dir_special}", xbmc.LOGINFO)
                    
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error verifying directories - {str(e)}", xbmc.LOGERROR)

    def periodic_update_check(self):
        """Perform periodic update checks"""
        try:
            current_time = time.time()
            
            if current_time - self.last_update_check >= self.update_check_interval:
                if self.wizard and hasattr(self.wizard, 'settings') and self.wizard.settings.get('auto_updates', True):
                    
                    def update_check_thread():
                        try:
                            if hasattr(self.wizard, 'periodic_update_check'):
                                self.wizard.periodic_update_check()
                        except Exception as e:
                            xbmc.log(f"CutCable Wizard Service: Error in periodic update check - {str(e)}", xbmc.LOGERROR)
                    
                    # Run in background thread
                    update_thread = threading.Thread(target=update_check_thread)
                    update_thread.daemon = True
                    update_thread.start()
                    
                    self.last_update_check = current_time
                    
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error in periodic update check - {str(e)}", xbmc.LOGERROR)

    def periodic_maintenance(self):
        """Perform periodic maintenance tasks"""
        try:
            current_time = time.time()
            
            if current_time - self.last_maintenance >= self.maintenance_interval:
                xbmc.log("CutCable Wizard Service: Performing periodic maintenance", xbmc.LOGDEBUG)
                
                # Clean up old backups
                if self.wizard and hasattr(self.wizard, 'cleanup_old_backups'):
                    self.wizard.cleanup_old_backups()
                
                # Clean temporary files
                self.cleanup_temp_files()
                
                # System health check
                self.system_health_check()
                
                self.last_maintenance = current_time
                
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error in periodic maintenance - {str(e)}", xbmc.LOGERROR)

    def memory_cleanup(self):
        """Perform memory cleanup and garbage collection"""
        try:
            current_time = time.time()
            
            if current_time - self.last_memory_cleanup >= self.memory_cleanup_interval:
                # Force garbage collection
                gc.collect()
                self.last_memory_cleanup = current_time
                
                xbmc.log("CutCable Wizard Service: Memory cleanup performed", xbmc.LOGDEBUG)
                
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error in memory cleanup - {str(e)}", xbmc.LOGERROR)

    def handle_settings_change(self):
        """Handle addon settings changes"""
        try:
            if self.wizard and hasattr(self.wizard, 'settings'):
                # Reload settings
                old_auto_updates = self.wizard.settings.get('auto_updates', True)
                if hasattr(self.wizard, 'load_settings'):
                    self.wizard.settings = self.wizard.load_settings()
                    new_auto_updates = self.wizard.settings.get('auto_updates', True)
                    
                    # Log settings change
                    if old_auto_updates != new_auto_updates:
                        status = "enabled" if new_auto_updates else "disabled"
                        xbmc.log(f"CutCable Wizard Service: Auto updates {status}", xbmc.LOGINFO)
                    
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error handling settings change - {str(e)}", xbmc.LOGERROR)

    def handle_library_update(self):
        """Handle library update events"""
        try:
            # Opportunity to perform post-library-update tasks
            xbmc.log("CutCable Wizard Service: Library update detected", xbmc.LOGDEBUG)
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error handling library update - {str(e)}", xbmc.LOGERROR)

    def main_service_loop(self):
        """Main service loop"""
        try:
            xbmc.log("CutCable Wizard Service: Starting main service loop", xbmc.LOGINFO)
            
            # Perform startup tasks in background
            startup_thread = threading.Thread(target=self.startup_tasks)
            startup_thread.daemon = True
            startup_thread.start()
            
            # Main service loop
            while not self.monitor.abortRequested() and self.running:
                
                # Periodic update checks
                self.periodic_update_check()
                
                # Periodic maintenance
                self.periodic_maintenance()
                
                # Memory cleanup
                self.memory_cleanup()
                
                # Wait for abort or interval
                if self.monitor.waitForAbort(30):  # Check every 30 seconds
                    break
            
            xbmc.log("CutCable Wizard Service: Service loop ended", xbmc.LOGINFO)
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error in main service loop - {str(e)}", xbmc.LOGERROR)

    def shutdown(self):
        """Service shutdown cleanup"""
        try:
            xbmc.log("CutCable Wizard Service: Shutting down service", xbmc.LOGINFO)
            
            self.running = False
            
            # Cleanup wizard instance
            if self.wizard and hasattr(self.wizard, 'cleanup'):
                self.wizard.cleanup()
                self.wizard = None
            
            # Final garbage collection
            gc.collect()
            
            xbmc.log("CutCable Wizard Service: Service shutdown complete", xbmc.LOGINFO)
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error during shutdown - {str(e)}", xbmc.LOGERROR)

class ServiceMonitor(xbmc.Monitor):
    """Custom monitor class for service events"""
    
    def __init__(self, service_instance):
        super(ServiceMonitor, self).__init__()
        self.service = service_instance

    def onSettingsChanged(self):
        """Called when addon settings are changed"""
        try:
            xbmc.log("CutCable Wizard Service: Settings changed", xbmc.LOGDEBUG)
            self.service.handle_settings_change()
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error in onSettingsChanged - {str(e)}", xbmc.LOGERROR)

    def onDatabaseUpdated(self, database):
        """Called when database is updated"""
        try:
            if database in ['video', 'music']:
                self.service.handle_library_update()
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error in onDatabaseUpdated - {str(e)}", xbmc.LOGERROR)

    def onNotification(self, sender, method, data):
        """Handle Kodi notifications"""
        try:
            # Handle specific notifications if needed
            if method == 'System.OnLowBattery':
                # Reduce service activity on low battery
                pass
            elif method == 'System.OnSleep':
                # Pause service activities
                pass
            elif method == 'System.OnWake':
                # Resume service activities
                pass
                
        except Exception as e:
            xbmc.log(f"CutCable Wizard Service: Error in onNotification - {str(e)}", xbmc.LOGERROR)

def main():
    """Main service entry point"""
    service = None
    monitor = None
    
    try:
        # Create service instance
        service = CutCableWizardService()
        
        # Create custom monitor
        monitor = ServiceMonitor(service)
        service.monitor = monitor
        
        # Start the main service loop
        service.main_service_loop()
        
    except Exception as e:
        xbmc.log(f"CutCable Wizard Service: Fatal error in service main - {str(e)}", xbmc.LOGERROR)
        
    finally:
        # Ensure cleanup happens
        if service:
            service.shutdown()
        
        # Final log
        xbmc.log("CutCable Wizard Service: Service terminated", xbmc.LOGINFO)

if __name__ == '__main__':
    main()
