#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
CutCable Build Wizard - Fire TV Optimized
Ultra-streamlined for novice users with maximum automation
"""

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import json
import urllib.request
import zipfile
import shutil
import hashlib
import traceback
import random
from datetime import datetime

class CutCableWizard:
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.userdata_path = xbmcvfs.translatePath('special://userdata/')
        self.settings_file = os.path.join(self.userdata_path, 'cutcable_settings.json')
        self.backup_path = os.path.join(self.userdata_path, 'cutcable_backup')
        self.version_file = os.path.join(self.userdata_path, 'cutcable_version.json')
        self.error_log = os.path.join(self.userdata_path, 'cutcable_error.log')
        self.deferred_file = os.path.join(self.userdata_path, 'cutcable_deferred.json')
        
        # Remote configuration
        self.config_url = 'https://gist.githubusercontent.com/FrugalITDad/555e8c564152c475b92340132c2159fd/raw/4deb98b93cc5a01a6f4d95d59220cdf5ac60988c/cutcable_config.json'
        self.builds_config = None
        
        # Fire TV optimizations
        self.is_firetv = 'amazon' in xbmc.getInfoLabel('System.BuildVersion').lower()
        self._setup_firetv_optimizations()
        
        # User-Agent pool for randomization
        self.user_agents = [
            'CutCable-FireTV/1.0',
            'CutCable-Kodi/1.0',
            'Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.36',
            'CutCable-Wizard/2.0 (Fire TV)',
            'Kodi/20.0 CutCable-Enhanced'
        ]
    
    def _log_error(self, error_msg, exception=None):
        """Enhanced error logging with stack traces"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            error_entry = f"\n[{timestamp}] {error_msg}\n"
            
            if exception:
                error_entry += f"Exception: {str(exception)}\n"
                error_entry += f"Stack Trace:\n{traceback.format_exc()}\n"
                error_entry += "-" * 50 + "\n"
            
            # Log to Kodi
            xbmc.log(f'CutCable Error: {error_msg}', xbmc.LOGERROR)
            
            # Save to error log file
            with open(self.error_log, 'a', encoding='utf-8') as f:
                f.write(error_entry)
                
        except Exception as log_error:
            xbmc.log(f'CutCable: Failed to log error - {str(log_error)}', xbmc.LOGERROR)
    
    def _get_random_user_agent(self):
        """Get random user agent for downloads"""
        return random.choice(self.user_agents)
        """Apply Fire TV specific optimizations"""
        if self.is_firetv:
            # Reduce UI animations for better performance
            xbmc.executebuiltin('SetSetting(lookandfeel.enablerssfeeds,false)')
            xbmc.executebuiltin('SetSetting(videoplayer.adjustrefreshrate,true)')
            xbmc.executebuiltin('SetSetting(videoplayer.pauseafterrefreshchange,0)')
            # Optimize cache for Fire TV
            xbmc.executebuiltin('SetSetting(cache.harddisk,256)')
            xbmc.executebuiltin('SetSetting(cache.internet,102400)')
    
    def _load_config(self):
        """Load build configuration with timeout optimization"""
        if self.builds_config:
            return True
        try:
            req = urllib.request.Request(self.config_url)
            req.add_header('User-Agent', self._get_random_user_agent())
            with urllib.request.urlopen(req, timeout=8) as response:
                self.builds_config = json.load(response)
                return True
        except Exception as e:
            self._log_error("Failed to load remote config", e)
            xbmcgui.Dialog().ok('Connection Error', 'Cannot connect to CutCable servers.\nCheck internet and try again.')
            return False
    
    def _verify_admin(self):
        """Streamlined admin verification"""
        if not self._load_config():
            return False
        password = xbmcgui.Dialog().input('Premium Access:', type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
        return password and hashlib.sha256(password.encode()).hexdigest() == self.builds_config.get('admin_password_hash', '')

    def show_main_menu(self):
        """Smart entry point - first run or returning user"""
        # Check for deferred installation first
        if self._check_deferred_install():
            return
            
        if not xbmcvfs.exists(self.settings_file):
            self._first_run_setup()
        else:
            self._returning_user_menu()

    def _first_run_setup(self):
        """Streamlined first run experience"""
        dialog = xbmcgui.Dialog()
        
        if not dialog.yesno('CutCable Wizard', 
                           'Welcome to CutCable!\n\n'
                           'This will install a custom Kodi build\n'
                           'and configure it for your Fire TV.\n\n'
                           'Continue?'):
            return
        
        # Load builds and show selection
        if self._load_config():
            self._show_build_selection()

    def _returning_user_menu(self):
        """Simplified menu for returning users"""
        options = ['Install Different Build', 'System Maintenance', 'Update Current Build', 'Auto Restore Last Build']
        choice = xbmcgui.Dialog().select('CutCable Wizard', options)
        
        if choice == 0:
            self._show_build_selection()
        elif choice == 1:
            self._run_maintenance()
        elif choice == 2:
            self._update_build()
        elif choice == 3:
            self._auto_restore_build()

    def _show_build_selection(self):
        """Streamlined build selection"""
        regular_builds = [b for b in self.builds_config['builds'] if not b.get('admin')]
        admin_builds = [b for b in self.builds_config['builds'] if b.get('admin')]
        
        # Create display list
        build_list = [f"{b['name']} - {b.get('description', 'Custom build')}" for b in regular_builds]
        if admin_builds:
            build_list.append('--- Premium Builds ---')
            build_list.extend([f"🔒 {b['name']} - {b.get('description', 'Premium build')}" for b in admin_builds])
        
        choice = xbmcgui.Dialog().select('Choose Your Build', build_list)
        if choice < 0:
            return
            
        # Handle selection
        if choice < len(regular_builds):
            self._install_build(regular_builds[choice])
        elif choice > len(regular_builds):  # Skip separator
            admin_idx = choice - len(regular_builds) - 1
            if self._verify_admin():
                self._install_build(admin_builds[admin_idx])
            else:
                xbmcgui.Dialog().ok('Access Denied', 'Invalid premium password.')

    def _install_build(self, build_info):
        """Complete build installation workflow"""
        dialog = xbmcgui.Dialog()
        
        # Check if system is busy
        if self._is_system_busy():
            if dialog.yesno('System Busy', 
                           'System appears busy. Install later?\n\n'
                           'This will schedule the installation for next startup.'):
                self._defer_installation(build_info)
                return
        
        # Confirmation
        if not dialog.yesno('Install Build', 
                           f'Install {build_info["name"]}?\n\n'
                           'Your settings will be backed up automatically.\n'
                           'This will restart Kodi when complete.'):
            return
        
        # Get user preferences (essential only)
        settings = self._get_user_preferences()
        if not settings:
            return
        
        # Install with progress
        self._perform_installation(build_info, settings)

    def _get_user_preferences(self):
        """Collect only essential user preferences"""
        dialog = xbmcgui.Dialog()
        settings = {}
        
        # Device name (auto-generate if skipped)
        device_name = dialog.input('Device Name (optional):', type=xbmcgui.INPUT_ALPHANUM)
        settings['device_name'] = device_name or f"FireTV-{os.urandom(2).hex().upper()}"
        
        # Audio setup - Fire TV specific options
        audio_opts = ['Auto (Recommended)', 'Stereo 2.0', 'Surround 5.1', 'Surround 7.1']
        audio_choice = dialog.select('Audio Output:', audio_opts)
        settings['audio'] = ['auto', '2.0', '5.1', '7.1'][audio_choice if audio_choice >= 0 else 0]
        
        # Subtitle preferences
        settings['subtitles'] = dialog.yesno('Subtitle Settings', 'Enable subtitles by default?')
        
        # Lyric display
        settings['lyrics'] = dialog.yesno('Music Settings', 'Show lyrics when playing music?')
        
        # Location for weather (optional)
        zip_code = dialog.input('ZIP Code for Weather (optional):', type=xbmcgui.INPUT_NUMERIC)
        if zip_code and len(zip_code) == 5:
            settings['zip_code'] = zip_code
        
        # Auto-enable Fire TV optimizations
        settings['firetv_optimized'] = True
        settings['auto_maintenance'] = True
        
        return settings

    def _perform_installation(self, build_info, settings):
        """Streamlined installation with progress"""
        progress = xbmcgui.DialogProgress()
        progress.create('Installing Build', f'Installing {build_info["name"]}...')
        
        try:
            # Create backup
            progress.update(10, 'Creating backup...')
            self._create_backup()
            
            # Clean system
            progress.update(20, 'Preparing system...')
            self._clean_system()
            
            # Download and install
            progress.update(30, 'Downloading build...')
            if not self._download_build(build_info, progress):
                raise Exception("Download failed")
            
            # Apply settings
            progress.update(90, 'Applying your settings...')
            self._apply_settings(settings)
            self._save_build_info(build_info, settings)
            
            progress.update(100, 'Installation complete!')
            progress.close()
            
            # Success and restart
            xbmcgui.Dialog().ok('Success!', 
                               f'{build_info["name"]} installed!\n\n'
                               'Kodi will restart now.')
            xbmc.executebuiltin('RestartApp')
            
        except Exception as e:
            progress.close()
            self._log_error(f"Installation failed for {build_info['name']}", e)
            xbmcgui.Dialog().ok('Installation Failed', 
                               'Installation failed.\nYour backup is safe.\nCheck error log for details.')
            # Offer to defer installation
            if xbmcgui.Dialog().yesno('Retry Later?', 
                                     'Would you like to retry this installation\n'
                                     'automatically on next startup?'):
                self._defer_installation(build_info)

    def _download_build(self, build_info, progress):
        """Optimized download with progress and versioning"""
        try:
            temp_file = os.path.join(self.userdata_path, 'temp_build.zip')
            req = urllib.request.Request(build_info['url'])
            req.add_header('User-Agent', self._get_random_user_agent())
            
            with urllib.request.urlopen(req, timeout=30) as response:
                total_size = int(response.getheader('Content-Length', 0))
                downloaded = 0
                
                with open(temp_file, 'wb') as f:
                    while True:
                        if progress.iscanceled():
                            return False
                        
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = 30 + int(50 * downloaded / total_size)
                            mb_down = downloaded / 1048576
                            mb_total = total_size / 1048576
                            progress.update(percent, f'Downloaded {mb_down:.1f}/{mb_total:.1f} MB')
            
            # Extract
            progress.update(85, 'Installing files...')
            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                zip_ref.extractall(self.userdata_path)
            
            os.remove(temp_file)
            return True
            
        except Exception as e:
            self._log_error("Build download failed", e)
            return False

    def _apply_settings(self, settings):
        """Apply user settings with Fire TV optimizations"""
        try:
            # Device name
            xbmc.executebuiltin(f'SetProperty(DeviceName,{settings["device_name"]},home)')
            
            # Audio settings
            if settings['audio'] != 'auto':
                xbmc.executebuiltin(f'SetSetting(audiooutput.channels,{settings["audio"]})')
            
            # Subtitle settings
            xbmc.executebuiltin(f'SetSetting(subtitles.show,{str(settings["subtitles"]).lower()})')
            
            # Lyric settings
            xbmc.executebuiltin(f'SetSetting(karaoke.enabled,{str(settings["lyrics"]).lower()})')
            
            # Fire TV optimizations
            if settings.get('firetv_optimized') and self.is_firetv:
                self._apply_firetv_optimizations()
            
            # Weather setup
            if settings.get('zip_code'):
                self._setup_weather(settings['zip_code'])
            
            # Save settings
            self._save_settings(settings)
            
        except Exception as e:
            self._log_error("Settings application failed", e)

    def _apply_firetv_optimizations(self):
        """Apply Fire TV specific performance optimizations"""
        try:
            optimizations = {
                'videoplayer.adjustrefreshrate': 'true',
                'videoplayer.pauseafterrefreshchange': '0',
                'lookandfeel.enablerssfeeds': 'false',
                'musicplayer.visualisation': 'None',
                'cache.harddisk': '256',
                'cache.internet': '102400',
                'network.usehttpproxy': 'false',
                'services.webserver': 'false'
            }
            
            for setting, value in optimizations.items():
                xbmc.executebuiltin(f'SetSetting({setting},{value})')
        except Exception as e:
            self._log_error("Fire TV optimizations failed", e)

    def _setup_weather(self, zip_code):
        """Setup weather with fallback addons"""
        weather_addons = ['weather.gismeteo', 'weather.openweathermap.extended', 'weather.yahoo']
        for addon_id in weather_addons:
            try:
                addon = xbmcaddon.Addon(addon_id)
                addon.setSetting('Location', zip_code)
                break
            except:
                continue

    def _create_backup(self):
        """Create essential backup"""
        try:
            if not xbmcvfs.exists(self.backup_path):
                xbmcvfs.mkdir(self.backup_path)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            backup_dir = os.path.join(self.backup_path, f'backup_{timestamp}')
            xbmcvfs.mkdir(backup_dir)
            
            # Backup essential items only
            essentials = ['addon_data', 'favourites.xml', 'sources.xml', 'keymaps']
            for item in essentials:
                src = os.path.join(self.userdata_path, item)
                dst = os.path.join(backup_dir, item)
                if xbmcvfs.exists(src):
                    try:
                        if os.path.isdir(src):
                            shutil.copytree(src, dst)
                        else:
                            shutil.copy2(src, dst)
                    except Exception as e:
                        self._log_error(f"Failed to backup {item}", e)
                        continue
            
            # Keep only 2 most recent backups
            self._cleanup_backups(keep=2)
            
        except Exception as e:
            self._log_error("Backup creation failed", e)

    def _cleanup_backups(self, keep=2):
        """Keep only the most recent backups"""
        try:
            if not xbmcvfs.exists(self.backup_path):
                return
            dirs, _ = xbmcvfs.listdir(self.backup_path)
            backups = sorted([d for d in dirs if d.startswith('backup_')], reverse=True)
            for old_backup in backups[keep:]:
                shutil.rmtree(os.path.join(self.backup_path, old_backup))
        except:
            pass

    def _clean_system(self):
        """Clean system before installation"""
        try:
            # Try to run K Cleaner silently
            xbmc.executebuiltin('RunScript(script.module.kcleaner,silent)', True)
        except:
            # Manual cleanup if K Cleaner not available
            cache_dirs = ['cache', 'temp', 'Thumbnails']
            for cache_dir in cache_dirs:
                cache_path = os.path.join(self.userdata_path, cache_dir)
                if xbmcvfs.exists(cache_path):
                    try:
                        shutil.rmtree(cache_path)
                        xbmcvfs.mkdir(cache_path)
                    except:
                        pass

    def _save_settings(self, settings):
        """Save user settings"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            xbmc.log(f'Save settings error: {str(e)}', xbmc.LOGERROR)

    def _save_build_info(self, build_info, settings):
        """Save build information"""
        try:
            info = {
                'build_name': build_info['name'],
                'build_url': build_info['url'],
                'installed_date': datetime.now().isoformat(),
                'user_settings': settings,
                'firetv_optimized': self.is_firetv
            }
            with open(self.version_file, 'w') as f:
                json.dump(info, f, indent=2)
        except Exception as e:
            xbmc.log(f'Save build info error: {str(e)}', xbmc.LOGERROR)

    def _run_maintenance(self):
        """One-click maintenance"""
        dialog = xbmcgui.Dialog()
        if dialog.yesno('System Maintenance', 
                       'Run system maintenance?\n\n'
                       '• Clean cache and temp files\n'
                       '• Optimize Fire TV performance\n'
                       '• Clean old backups'):
            
            progress = xbmcgui.DialogProgress()
            progress.create('Maintenance', 'Optimizing system...')
            
            progress.update(25, 'Cleaning cache...')
            self._clean_system()
            
            progress.update(50, 'Optimizing Fire TV...')
            if self.is_firetv:
                self._apply_firetv_optimizations()
            
            progress.update(75, 'Cleaning backups...')
            self._cleanup_backups()
            
            progress.update(100, 'Complete!')
            progress.close()
            
            dialog.ok('Maintenance Complete', 'Your Fire TV is now optimized!')

    def _update_build(self):
        """Update current build"""
        try:
            if not xbmcvfs.exists(self.version_file):
                xbmcgui.Dialog().ok('No Build Found', 'No CutCable build detected.')
                return
            
            with open(self.version_file, 'r') as f:
                current_info = json.load(f)
            
            if self._load_config():
                current_build = next((b for b in self.builds_config['builds'] 
                                    if b['name'] == current_info['build_name']), None)
                if current_build:
                    # Use saved settings for update
                    self._perform_installation(current_build, current_info.get('user_settings', {}))
                else:
                    xbmcgui.Dialog().ok('Build Unavailable', 'Your build is no longer available.')
        except Exception as e:
            xbmc.log(f'Update error: {str(e)}', xbmc.LOGERROR)

    def startup_maintenance(self):
        """Auto maintenance on startup (runs silently)"""
        try:
            if not xbmcvfs.exists(self.version_file):
                return
            
            # Run silent maintenance once per day
            with open(self.version_file, 'r') as f:
                build_info = json.load(f)
            
            last_maintenance = build_info.get('last_maintenance', '2000-01-01')
            today = datetime.now().strftime('%Y-%m-%d')
            
            if last_maintenance != today:
                # Silent system optimization
                if self.is_firetv:
                    self._apply_firetv_optimizations()
                self._cleanup_backups()
                
                # Update maintenance date
                build_info['last_maintenance'] = today
                with open(self.version_file, 'w') as f:
                    json.dump(build_info, f, indent=2)
                    
        except Exception as e:
            xbmc.log(f'Startup maintenance error: {str(e)}', xbmc.LOGERROR)


# Main execution
if __name__ == '__main__':
    wizard = CutCableWizard()
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'startup':
        wizard.startup_maintenance()
    else:
        wizard.show_main_menu()
