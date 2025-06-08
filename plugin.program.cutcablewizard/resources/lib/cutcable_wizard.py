#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
CutCable Wizard - Main Wizard Class
Optimized for Fire TV devices with comprehensive build management
"""

import os
import sys
import json
import hashlib
import zipfile
import shutil
import time
import threading
import gc
from urllib.parse import urlparse
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import requests

class CutCableWizard:
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.addon_path = self.addon.getAddonInfo('path')
        self.addon_data_path = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
        self.kodi_home = xbmcvfs.translatePath('special://home/')
        self.temp_path = xbmcvfs.translatePath('special://temp/')
        
        # Ensure required directories exist
        for path in [self.addon_data_path, self.temp_path]:
            if not xbmcvfs.exists(path):
                xbmcvfs.mkdirs(path)
        
        # Configuration URLs
        self.builds_gist_url = "https://gist.githubusercontent.com/FrugalITDad/555e8c564152c475b92340132c2159fd/raw/4deb98b93cc5a01a6f4d95d59220cdf5ac60988c/cutcable_config.json"
        self.repo_base_url = "https://raw.githubusercontent.com/FrugalITDad/FrugalITDad/main/wizard/"
        
        # Local storage paths
        self.settings_file = os.path.join(self.addon_data_path, 'wizard_settings.json')
        self.build_info_file = os.path.join(self.addon_data_path, 'current_build.json')
        self.backup_path = os.path.join(self.addon_data_path, 'backups')
        
        # Ensure backup directory exists
        if not xbmcvfs.exists(self.backup_path):
            xbmcvfs.mkdirs(self.backup_path)
        
        # Load current settings and build info
        self.settings = self.load_settings()
        self.build_info = self.load_build_info()
        
        # Fire TV optimizations
        self.chunk_size = 1024 * 64  # 64KB chunks for streaming
        self.max_retries = 3
        self.request_timeout = 30
        
        xbmc.log("CutCable Wizard: Initialized successfully", xbmc.LOGINFO)

    def load_settings(self):
        """Load wizard settings from file"""
        default_settings = {
            'first_run_complete': False,
            'subtitles_enabled': True,
            'lyrics_auto_display': True,
            'device_name': '',
            'zip_code': '',
            'audio_channels': '2.0',
            'last_update_check': 0,
            'auto_updates': True,
            'current_build': None,
            'wizard_version': '1.0.0'
        }
        
        try:
            if xbmcvfs.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults to handle missing keys
                    default_settings.update(loaded_settings)
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error loading settings - {str(e)}", xbmc.LOGERROR)
        
        return default_settings

    def save_settings(self):
        """Save wizard settings to file"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error saving settings - {str(e)}", xbmc.LOGERROR)
            return False

    def load_build_info(self):
        """Load current build information"""
        default_info = {
            'installed_build': None,
            'version': None,
            'install_date': None,
            'last_backup': None
        }
        
        try:
            if xbmcvfs.exists(self.build_info_file):
                with open(self.build_info_file, 'r', encoding='utf-8') as f:
                    loaded_info = json.load(f)
                    default_info.update(loaded_info)
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error loading build info - {str(e)}", xbmc.LOGERROR)
        
        return default_info

    def save_build_info(self, build_name, version=None):
        """Save current build information"""
        try:
            self.build_info.update({
                'installed_build': build_name,
                'version': version or self.extract_version_from_name(build_name),
                'install_date': int(time.time())
            })
            
            with open(self.build_info_file, 'w', encoding='utf-8') as f:
                json.dump(self.build_info, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error saving build info - {str(e)}", xbmc.LOGERROR)
            return False

    def extract_version_from_name(self, build_name):
        """Extract version from build filename"""
        try:
            import re
            version_match = re.search(r'v(\d+\.\d+(?:\.\d+)?)', build_name.lower())
            if version_match:
                return version_match.group(1)
        except:
            pass
        return "1.0"

    def compare_versions(self, version1, version2):
        """Compare two version strings. Returns: 1 if v1 > v2, -1 if v1 < v2, 0 if equal"""
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))
            
            for v1, v2 in zip(v1_parts, v2_parts):
                if v1 > v2:
                    return 1
                elif v1 < v2:
                    return -1
            return 0
        except:
            return 0

    def check_connectivity(self):
        """Check connectivity to all required services"""
        services = [
            ("GitHub Gist", self.builds_gist_url),
            ("GitHub Repository", self.repo_base_url + "plugin.program.cutcable.wizard/addon.xml")
        ]
        
        failed_services = []
        
        for name, url in services:
            try:
                response = requests.head(url, timeout=10)
                if response.status_code not in [200, 302]:
                    failed_services.append(name)
            except:
                failed_services.append(name)
        
        return len(failed_services) == 0, failed_services

    def fetch_builds_list(self):
        """Fetch available builds from GitHub Gist with retry logic"""
        for attempt in range(self.max_retries):
            try:
                xbmc.log(f"CutCable Wizard: Fetching builds list (attempt {attempt + 1})", xbmc.LOGDEBUG)
                response = requests.get(self.builds_gist_url, timeout=self.request_timeout)
                response.raise_for_status()
                builds_data = response.json()
                
                # Validate builds data structure
                if 'builds' not in builds_data:
                    raise ValueError("Invalid builds data structure")
                
                return builds_data
                
            except Exception as e:
                xbmc.log(f"CutCable Wizard: Error fetching builds list (attempt {attempt + 1}) - {str(e)}", xbmc.LOGERROR)
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                break
        
        return None

    def verify_admin_password(self, password):
        """Verify admin password against stored hash"""
        try:
            builds_data = self.fetch_builds_list()
            if not builds_data or 'admin_password_hash' not in builds_data:
                return False
            
            password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            return password_hash == builds_data['admin_password_hash']
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error verifying admin password - {str(e)}", xbmc.LOGERROR)
            return False

    def create_backup(self):
        """Create backup of critical userdata"""
        try:
            backup_name = f"backup_{int(time.time())}"
            backup_dir = os.path.join(self.backup_path, backup_name)
            
            if not xbmcvfs.exists(backup_dir):
                xbmcvfs.mkdirs(backup_dir)
            
            # Critical paths to backup
            userdata_path = xbmcvfs.translatePath('special://userdata/')
            backup_items = [
                ('addon_data', os.path.join(userdata_path, 'addon_data')),
                ('Database', os.path.join(userdata_path, 'Database')),
                ('sources.xml', os.path.join(userdata_path, 'sources.xml')),
                ('favourites.xml', os.path.join(userdata_path, 'favourites.xml')),
                ('advancedsettings.xml', os.path.join(userdata_path, 'advancedsettings.xml'))
            ]
            
            progress = xbmcgui.DialogProgress()
            progress.create("CutCable Wizard", "Creating backup...")
            
            total_items = len(backup_items)
            
            for i, (name, source_path) in enumerate(backup_items):
                if progress.iscanceled():
                    break
                
                progress.update(int((i / total_items) * 100), f"Backing up {name}...")
                
                if xbmcvfs.exists(source_path):
                    dest_path = os.path.join(backup_dir, name)
                    if os.path.isdir(source_path):
                        shutil.copytree(source_path, dest_path, ignore_errors=True)
                    else:
                        shutil.copy2(source_path, dest_path)
                
                # Force garbage collection to manage memory
                if i % 2 == 0:
                    gc.collect()
            
            progress.close()
            
            # Clean up old backups (keep last 3)
            self.cleanup_old_backups()
            
            self.build_info['last_backup'] = backup_name
            return backup_name
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error creating backup - {str(e)}", xbmc.LOGERROR)
            if 'progress' in locals():
                progress.close()
            return None

    def restore_backup(self, backup_name=None):
        """Restore from backup"""
        try:
            if not backup_name:
                backup_name = self.build_info.get('last_backup')
            
            if not backup_name:
                return False
            
            backup_dir = os.path.join(self.backup_path, backup_name)
            if not xbmcvfs.exists(backup_dir):
                return False
            
            progress = xbmcgui.DialogProgress()
            progress.create("CutCable Wizard", "Restoring backup...")
            
            userdata_path = xbmcvfs.translatePath('special://userdata/')
            
            # Restore critical items
            restore_items = [
                ('addon_data', os.path.join(userdata_path, 'addon_data')),
                ('Database', os.path.join(userdata_path, 'Database')),
                ('sources.xml', os.path.join(userdata_path, 'sources.xml')),
                ('favourites.xml', os.path.join(userdata_path, 'favourites.xml')),
                ('advancedsettings.xml', os.path.join(userdata_path, 'advancedsettings.xml'))
            ]
            
            total_items = len(restore_items)
            
            for i, (name, dest_path) in enumerate(restore_items):
                if progress.iscanceled():
                    break
                
                progress.update(int((i / total_items) * 100), f"Restoring {name}...")
                
                source_path = os.path.join(backup_dir, name)
                if xbmcvfs.exists(source_path):
                    if os.path.exists(dest_path):
                        if os.path.isdir(dest_path):
                            shutil.rmtree(dest_path, ignore_errors=True)
                        else:
                            os.remove(dest_path)
                    
                    if os.path.isdir(source_path):
                        shutil.copytree(source_path, dest_path, ignore_errors=True)
                    else:
                        shutil.copy2(source_path, dest_path)
                
                # Memory management
                if i % 2 == 0:
                    gc.collect()
            
            progress.close()
            return True
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error restoring backup - {str(e)}", xbmc.LOGERROR)
            if 'progress' in locals():
                progress.close()
            return False

    def cleanup_old_backups(self, keep_count=3):
        """Clean up old backups, keeping only the most recent ones"""
        try:
            if not xbmcvfs.exists(self.backup_path):
                return
            
            # Get all backup directories
            backups = []
            dirs, files = xbmcvfs.listdir(self.backup_path)
            
            for dir_name in dirs:
                if dir_name.startswith('backup_'):
                    backup_path = os.path.join(self.backup_path, dir_name)
                    try:
                        timestamp = int(dir_name.split('_')[1])
                        backups.append((timestamp, backup_path))
                    except:
                        continue
            
            # Sort by timestamp (newest first) and remove old ones
            backups.sort(reverse=True)
            
            for i, (timestamp, backup_path) in enumerate(backups):
                if i >= keep_count:
                    try:
                        shutil.rmtree(backup_path, ignore_errors=True)
                        xbmc.log(f"CutCable Wizard: Removed old backup: {backup_path}", xbmc.LOGDEBUG)
                    except:
                        pass
        
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error cleaning up backups - {str(e)}", xbmc.LOGERROR)

    def download_file(self, url, destination, description="Downloading"):
        """Download file with progress dialog and streaming"""
        try:
            response = requests.get(url, stream=True, timeout=self.request_timeout)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            progress = xbmcgui.DialogProgress()
            progress.create("CutCable Wizard", description)
            
            downloaded = 0
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if progress.iscanceled():
                        response.close()
                        if os.path.exists(destination):
                            os.remove(destination)
                        return False
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            progress.update(percent, 
                                          f"{description}\n{downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB")
                        else:
                            progress.update(0, f"{description}\n{downloaded // (1024*1024)}MB downloaded")
                    
                    # Memory management for large files
                    if downloaded % (1024 * 1024 * 5) == 0:  # Every 5MB
                        gc.collect()
            
            progress.close()
            return True
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error downloading file - {str(e)}", xbmc.LOGERROR)
            if 'progress' in locals():
                progress.close()
            if os.path.exists(destination):
                os.remove(destination)
            return False

    def extract_build(self, zip_path, extract_to):
        """Extract build zip file with progress"""
        try:
            progress = xbmcgui.DialogProgress()
            progress.create("CutCable Wizard", "Extracting build...")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                total_files = len(file_list)
                
                for i, file_name in enumerate(file_list):
                    if progress.iscanceled():
                        return False
                    
                    progress.update(int((i / total_files) * 100), 
                                  f"Extracting...\n{os.path.basename(file_name)}")
                    
                    try:
                        zip_ref.extract(file_name, extract_to)
                    except:
                        # Skip problematic files
                        continue
                    
                    # Memory management
                    if i % 50 == 0:
                        gc.collect()
            
            progress.close()
            return True
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error extracting build - {str(e)}", xbmc.LOGERROR)
            if 'progress' in locals():
                progress.close()
            return False

    def install_build(self, build_info):
        """Install a build with full error handling and recovery"""
        build_name = build_info['name']
        build_url = build_info['url']
        
        try:
            # Check connectivity first
            connectivity_ok, failed_services = self.check_connectivity()
            if not connectivity_ok:
                xbmcgui.Dialog().ok("Connection Error", 
                                  f"Cannot connect to required services:\n{', '.join(failed_services)}")
                return False
            
            # Create backup before installation
            xbmc.log("CutCable Wizard: Creating backup before installation", xbmc.LOGINFO)
            backup_name = self.create_backup()
            if not backup_name:
                if not xbmcgui.Dialog().yesno("Backup Failed", 
                                            "Could not create backup. Continue with installation?"):
                    return False
            
            # Download build
            temp_zip = os.path.join(self.temp_path, f"build_{int(time.time())}.zip")
            
            xbmc.log(f"CutCable Wizard: Downloading build {build_name}", xbmc.LOGINFO)
            if not self.download_file(build_url, temp_zip, f"Downloading {build_name}"):
                xbmcgui.Dialog().ok("Download Failed", "Could not download the build file.")
                return False
            
            # Extract to temporary location
            temp_extract = os.path.join(self.temp_path, f"extract_{int(time.time())}")
            if not xbmcvfs.exists(temp_extract):
                xbmcvfs.mkdirs(temp_extract)
            
            xbmc.log("CutCable Wizard: Extracting build", xbmc.LOGINFO)
            if not self.extract_build(temp_zip, temp_extract):
                xbmcgui.Dialog().ok("Extraction Failed", "Could not extract the build file.")
                self.cleanup_temp_files([temp_zip, temp_extract])
                return False
            
            # Save build info before Kodi restart
            self.save_build_info(build_name)
            self.settings['current_build'] = build_name
            self.save_settings()
            
            # Create installation marker for post-restart processing
            install_marker = {
                'temp_extract': temp_extract,
                'temp_zip': temp_zip,
                'build_name': build_name,
                'backup_name': backup_name,
                'install_time': int(time.time())
            }
            
            marker_file = os.path.join(self.addon_data_path, 'install_marker.json')
            with open(marker_file, 'w', encoding='utf-8') as f:
                json.dump(install_marker, f, indent=2)
            
            # Notify user about restart
            xbmcgui.Dialog().ok("Installation Ready", 
                              f"Build {build_name} is ready to install.\nKodi will now restart to complete the installation.")
            
            # Force Kodi restart
            xbmc.executebuiltin('RestartApp')
            return True
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error during build installation - {str(e)}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok("Installation Error", f"An error occurred during installation:\n{str(e)}")
            return False

    def complete_installation(self):
        """Complete installation after Kodi restart"""
        marker_file = os.path.join(self.addon_data_path, 'install_marker.json')
        
        if not xbmcvfs.exists(marker_file):
            return
        
        try:
            with open(marker_file, 'r', encoding='utf-8') as f:
                install_data = json.load(f)
            
            temp_extract = install_data['temp_extract']
            temp_zip = install_data['temp_zip']
            build_name = install_data['build_name']
            backup_name = install_data.get('backup_name')
            
            if not xbmcvfs.exists(temp_extract):
                xbmc.log("CutCable Wizard: Extracted files not found, installation may have failed", xbmc.LOGERROR)
                os.remove(marker_file)
                return
            
            # Copy extracted files to Kodi home
            progress = xbmcgui.DialogProgress()
            progress.create("CutCable Wizard", "Completing installation...")
            
            success = self.copy_build_files(temp_extract, self.kodi_home, progress)
            progress.close()
            
            if success:
                # Cleanup temporary files
                self.cleanup_temp_files([temp_zip, temp_extract])
                
                # Remove install marker
                os.remove(marker_file)
                
                # Update build info
                self.save_build_info(build_name)
                
                # Show completion notification
                xbmc.executebuiltin(f'Notification(CutCable Wizard, Build {build_name} installed successfully!, 5000)')
                
                # Check if first run setup needed
                if not self.settings.get('first_run_complete'):
                    self.first_run_setup()
                
                xbmc.log(f"CutCable Wizard: Build {build_name} installation completed successfully", xbmc.LOGINFO)
            else:
                # Installation failed, attempt restore
                if backup_name:
                    self.restore_backup(backup_name)
                    xbmc.executebuiltin('Notification(CutCable Wizard, Installation failed - backup restored, 5000)')
                else:
                    xbmc.executebuiltin('Notification(CutCable Wizard, Installation failed, 5000)')
                
                os.remove(marker_file)
                
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error completing installation - {str(e)}", xbmc.LOGERROR)
            if os.path.exists(marker_file):
                os.remove(marker_file)

    def copy_build_files(self, source_dir, dest_dir, progress_dialog=None):
        """Copy build files from source to destination with progress"""
        try:
            # Get all files to copy
            all_files = []
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    source_file = os.path.join(root, file)
                    rel_path = os.path.relpath(source_file, source_dir)
                    dest_file = os.path.join(dest_dir, rel_path)
                    all_files.append((source_file, dest_file))
            
            total_files = len(all_files)
            
            for i, (source_file, dest_file) in enumerate(all_files):
                if progress_dialog and progress_dialog.iscanceled():
                    return False
                
                # Create destination directory if needed
                dest_dir_path = os.path.dirname(dest_file)
                if not os.path.exists(dest_dir_path):
                    os.makedirs(dest_dir_path, exist_ok=True)
                
                # Copy file
                try:
                    shutil.copy2(source_file, dest_file)
                except:
                    # Skip problematic files
                    continue
                
                if progress_dialog:
                    percent = int((i / total_files) * 100)
                    progress_dialog.update(percent, f"Installing files...\n{os.path.basename(dest_file)}")
                
                # Memory management
                if i % 100 == 0:
                    gc.collect()
            
            return True
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error copying build files - {str(e)}", xbmc.LOGERROR)
            return False

    def cleanup_temp_files(self, file_paths):
        """Clean up temporary files and directories"""
        for path in file_paths:
            try:
                if os.path.exists(path):
                    if os.path.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                    else:
                        os.remove(path)
            except:
                pass

    def first_run_setup(self):
        """First run setup wizard"""
        try:
            xbmc.log("CutCable Wizard: Starting first run setup", xbmc.LOGINFO)
            
            dialog = xbmcgui.Dialog()
            
            # Welcome message
            dialog.ok("Welcome to CutCable Wizard", 
                     "Let's configure your build with some initial settings.")
            
            # Device name
            device_name = dialog.input("Device Name", 
                                     "Enter a name for this device (max 15 characters):",
                                     type=xbmcgui.INPUT_ALPHANUM)
            if device_name:
                self.settings['device_name'] = device_name[:15]
            
            # Subtitles
            subtitles_enabled = dialog.yesno("Subtitles", "Enable subtitles by default?")
            self.settings['subtitles_enabled'] = subtitles_enabled
            
            # Music lyrics
            lyrics_enabled = dialog.yesno("Music Lyrics", 
                                        "Display lyrics automatically when playing music?\n(CU LRC Lyrics)")
            self.settings['lyrics_auto_display'] = lyrics_enabled
            
            # Audio channels
            audio_options = ['2.0 (Stereo)', '5.1 (Surround)', '7.1 (Full Surround)']
            audio_choice = dialog.select("Audio Channels", audio_options)
            if audio_choice >= 0:
                audio_values = ['2.0', '5.1', '7.1']
                self.settings['audio_channels'] = audio_values[audio_choice]
            
            # Zip code for weather
            zip_code = dialog.input("Weather Location", 
                                  "Enter your zip code for weather updates:",
                                  type=xbmcgui.INPUT_NUMERIC)
            if zip_code:
                self.settings['zip_code'] = zip_code
            
            # Apply settings to Kodi
            self.apply_first_run_settings()
            
            # Mark first run as complete
            self.settings['first_run_complete'] = True
            self.save_settings()
            
            dialog.ok("Setup Complete", "Your CutCable build is now configured and ready to use!")
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error in first run setup - {str(e)}", xbmc.LOGERROR)

    def apply_first_run_settings(self):
        """Apply first run settings to Kodi configuration"""
        try:
            # Configure subtitles
            if self.settings.get('subtitles_enabled'):
                xbmc.executebuiltin('SetGUILanguage(resource.language.en_gb)')
                
            # Configure audio channels
            audio_channels = self.settings.get('audio_channels', '2.0')
            if audio_channels == '5.1':
                xbmc.executebuiltin('SetAudioDSPSetting(channels, 6)')
            elif audio_channels == '7.1':
                xbmc.executebuiltin('SetAudioDSPSetting(channels, 8)')
            
            # Set device name if supported
            device_name = self.settings.get('device_name')
            if device_name:
                # This would be build-specific implementation
                pass
            
            # Configure weather addon with zip code
            zip_code = self.settings.get('zip_code')
            if zip_code:
                # Configure Gismeteo weather addon
                try:
                    weather_addon = xbmcaddon.Addon('weather.gismeteo')
                    weather_addon.setSetting('Location', zip_code)
                except:
                    pass
            
            # Configure CU LRC Lyrics
            if self.settings.get('lyrics_auto_display'):
                try:
                    lyrics_addon = xbmcaddon.Addon('script.cu.lrclyrics')
                    lyrics_addon.setSetting('auto_show', 'true')
                except:
                    pass
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error applying first run settings - {str(e)}", xbmc.LOGERROR)

    def show_main_menu(self):
        """Display the main wizard menu - Fire TV optimized"""
        try:
            # Check for pending installation completion
            marker_file = os.path.join(self.addon_data_path, 'install_marker.json')
            if xbmcvfs.exists(marker_file):
                self.complete_installation()
                return
            
            # Check connectivity
            connectivity_ok, failed_services = self.check_connectivity()
            if not connectivity_ok:
                xbmcgui.Dialog().ok("Connection Error", 
                                  f"Cannot connect to:\n{', '.join(failed_services)}\n\nPlease check your internet connection.")
                return
            
            while True:
                # Main menu options
                menu_items = [
                    "Install/Update Build",
                    "Maintenance Tools",
                    "Build Information",
                    "Settings",
                    "About"
                ]
                
                choice = xbmcgui.Dialog().select("CutCable Wizard - Main Menu", menu_items)
                
                if choice == -1:  # User cancelled
                    break
                elif choice == 0:  # Install/Update Build
                    self.show_build_menu()
                elif choice == 1:  # Maintenance Tools
                    self.show_maintenance_menu()
                elif choice == 2:  # Build Information
                    self.show_build_info()
                elif choice == 3:  # Settings
                    self.show_settings_menu()
                elif choice == 4:  # About
                    self.show_about()
                
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error in main menu - {str(e)}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok("Error", f"An error occurred: {str(e)}")

    def show_build_menu(self):
        """Display build selection menu"""
        try:
            builds_data = self.fetch_builds_list()
            if not builds_data:
                xbmcgui.Dialog().ok("Error", "Could not fetch builds list. Please check your connection.")
                return
            
            builds = builds_data.get('builds', [])
            if not builds:
                xbmcgui.Dialog().ok("Error", "No builds available.")
                return
            
            # Prepare build menu items
            menu_items = []
            build_objects = []
            
            current_build = self.build_info.get('installed_build', '')
            current_version = self.build_info.get('version', '1.0')
            
            for build in builds:
                build_name = build['name']
                build_version = self.extract_version_from_name(build_name)
                is_admin = build.get('admin', False)
                
                # Format display name
                display_name = build_name.replace('.zip', '').replace('-', ' ').title()
                
                # Check if this is current build and if update available
                if build_name == current_build:
                    if self.compare_versions(build_version, current_version) > 0:
                        display_name += f" (UPDATE AVAILABLE - v{build_version})"
                    else:
                        display_name += " (INSTALLED)"
                else:
                    display_name += f" (v{build_version})"
                
                if is_admin:
                    display_name += " [ADMIN]"
                
                menu_items.append(display_name)
                build_objects.append(build)
            
            choice = xbmcgui.Dialog().select("Select Build to Install", menu_items)
            
            if choice >= 0:
                selected_build = build_objects[choice]
                
                # Check if admin build requires password
                if selected_build.get('admin', False):
                    if not self.handle_admin_authentication():
                        return
                
                # Confirm installation
                build_display_name = menu_items[choice]
                if xbmcgui.Dialog().yesno("Confirm Installation", 
                                        f"Install {build_display_name}?\n\nThis will backup your current settings and restart Kodi."):
                    self.install_build(selected_build)
                
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error in build menu - {str(e)}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok("Error", f"An error occurred: {str(e)}")

    def handle_admin_authentication(self):
        """Handle admin build password authentication"""
        attempts = 0
        max_attempts = 3
        
        while attempts < max_attempts:
            password = xbmcgui.Dialog().input("Admin Access Required", 
                                            f"Enter admin password (Attempt {attempts + 1}/{max_attempts}):",
                                            type=xbmcgui.INPUT_ALPHANUM,
                                            option=xbmcgui.ALPHANUM_HIDE_INPUT)
            
            if not password:  # User cancelled
                return False
            
            if self.verify_admin_password(password):
                return True
            
            attempts += 1
            
            if attempts < max_attempts:
                xbmcgui.Dialog().ok("Invalid Password", f"Incorrect password. {max_attempts - attempts} attempts remaining.")
            else:
                xbmcgui.Dialog().ok("Access Denied", "Maximum password attempts exceeded.")
        
        return False

    def show_maintenance_menu(self):
        """Display maintenance tools menu"""
        try:
            menu_items = [
                "Run K Cleaner",
                "Clear Addon Data",
                "Force Update Check",
                "Restore from Backup",
                "Clean Temp Files"
            ]
            
            choice = xbmcgui.Dialog().select("Maintenance Tools", menu_items)
            
            if choice == -1:
                return
            elif choice == 0:  # Run K Cleaner
                self.run_k_cleaner()
            elif choice == 1:  # Clear Addon Data
                self.clear_addon_data()
            elif choice == 2:  # Force Update Check
                self.force_update_check()
            elif choice == 3:  # Restore from Backup
                self.show_restore_menu()
            elif choice == 4:  # Clean Temp Files
                self.clean_temp_files_manual()
                
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error in maintenance menu - {str(e)}", xbmc.LOGERROR)

    def run_k_cleaner(self):
        """Run K Cleaner addon"""
        try:
            if xbmcgui.Dialog().yesno("K Cleaner", "Run K Cleaner to clean cache and temporary files?"):
                # Try to run K Cleaner addon
                xbmc.executebuiltin('RunAddon(script.module.kclean)')
                xbmc.executebuiltin('Notification(CutCable Wizard, K Cleaner started, 3000)')
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error running K Cleaner - {str(e)}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok("Error", "Could not run K Cleaner. Please run it manually from the addons menu.")

    def clear_addon_data(self):
        """Clear addon data with confirmation"""
        try:
            if xbmcgui.Dialog().yesno("Clear Addon Data", 
                                    "This will reset all addon settings.\nThis action cannot be undone.\n\nContinue?"):
                addon_data_path = xbmcvfs.translatePath('special://userdata/addon_data/')
                
                progress = xbmcgui.DialogProgress()
                progress.create("CutCable Wizard", "Clearing addon data...")
                
                try:
                    # Remove addon_data contents but preserve structure
                    for item in os.listdir(addon_data_path):
                        item_path = os.path.join(addon_data_path, item)
                        if os.path.isdir(item_path):
                            # Skip wizard addon data
                            if 'cutcable.wizard' not in item:
                                shutil.rmtree(item_path, ignore_errors=True)
                    
                    progress.close()
                    xbmcgui.Dialog().ok("Complete", "Addon data cleared successfully.")
                    
                except Exception as e:
                    progress.close()
                    xbmcgui.Dialog().ok("Error", f"Could not clear addon data: {str(e)}")
                    
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error clearing addon data - {str(e)}", xbmc.LOGERROR)

    def force_update_check(self):
        """Force an immediate update check"""
        try:
            progress = xbmcgui.DialogProgress()
            progress.create("CutCable Wizard", "Checking for updates...")
            
            # Check for wizard updates
            wizard_updated = self.check_wizard_update()
            
            # Check for build updates
            build_updates = self.check_build_updates()
            
            progress.close()
            
            if wizard_updated:
                xbmcgui.Dialog().ok("Wizard Updated", "The wizard has been updated. Please restart Kodi.")
            elif build_updates:
                if xbmcgui.Dialog().yesno("Build Update Available", 
                                        f"A new version of your build is available.\nInstall update now?"):
                    self.install_build(build_updates)
            else:
                xbmcgui.Dialog().ok("No Updates", "No updates are available at this time.")
                
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error in force update check - {str(e)}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok("Error", f"Update check failed: {str(e)}")

    def show_restore_menu(self):
        """Show available backups for restore"""
        try:
            if not xbmcvfs.exists(self.backup_path):
                xbmcgui.Dialog().ok("No Backups", "No backups are available.")
                return
            
            # Get available backups
            backups = []
            dirs, files = xbmcvfs.listdir(self.backup_path)
            
            for dir_name in dirs:
                if dir_name.startswith('backup_'):
                    try:
                        timestamp = int(dir_name.split('_')[1])
                        backup_date = time.strftime('%Y-%m-%d %H:%M', time.localtime(timestamp))
                        backups.append((timestamp, dir_name, backup_date))
                    except:
                        continue
            
            if not backups:
                xbmcgui.Dialog().ok("No Backups", "No valid backups found.")
                return
            
            # Sort by timestamp (newest first)
            backups.sort(reverse=True)
            
            # Create menu
            menu_items = [f"Backup from {backup_date}" for _, _, backup_date in backups]
            
            choice = xbmcgui.Dialog().select("Select Backup to Restore", menu_items)
            
            if choice >= 0:
                selected_backup = backups[choice][1]
                
                if xbmcgui.Dialog().yesno("Confirm Restore", 
                                        f"Restore backup from {backups[choice][2]}?\n\nThis will overwrite current settings."):
                    if self.restore_backup(selected_backup):
                        xbmcgui.Dialog().ok("Restore Complete", "Backup restored successfully. Restart Kodi to apply changes.")
                    else:
                        xbmcgui.Dialog().ok("Restore Failed", "Could not restore the selected backup.")
                        
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error in restore menu - {str(e)}", xbmc.LOGERROR)

    def clean_temp_files_manual(self):
        """Manually clean temporary files"""
        try:
            if xbmcgui.Dialog().yesno("Clean Temp Files", "Remove temporary files and clear cache?"):
                progress = xbmcgui.DialogProgress()
                progress.create("CutCable Wizard", "Cleaning temporary files...")
                
                cleaned_size = 0
                
                # Clean wizard temp files
                temp_files = []
                if os.path.exists(self.temp_path):
                    for item in os.listdir(self.temp_path):
                        if item.startswith(('build_', 'extract_')):
                            temp_files.append(os.path.join(self.temp_path, item))
                
                for temp_file in temp_files:
                    try:
                        if os.path.isdir(temp_file):
                            cleaned_size += sum(os.path.getsize(os.path.join(dirpath, filename))
                                              for dirpath, dirnames, filenames in os.walk(temp_file)
                                              for filename in filenames)
                            shutil.rmtree(temp_file, ignore_errors=True)
                        else:
                            cleaned_size += os.path.getsize(temp_file)
                            os.remove(temp_file)
                    except:
                        pass
                
                progress.close()
                
                cleaned_mb = cleaned_size // (1024 * 1024)
                xbmcgui.Dialog().ok("Cleanup Complete", f"Cleaned {cleaned_mb}MB of temporary files.")
                
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error cleaning temp files - {str(e)}", xbmc.LOGERROR)

    def show_build_info(self):
        """Display current build information"""
        try:
            current_build = self.build_info.get('installed_build', 'None')
            current_version = self.build_info.get('version', 'Unknown')
            install_date = self.build_info.get('install_date')
            
            if install_date:
                install_date_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(install_date))
            else:
                install_date_str = 'Unknown'
            
            info_text = f"""Current Build: {current_build}
Version: {current_version}
Installed: {install_date_str}
Device: {self.settings.get('device_name', 'Not set')}
Auto Updates: {'Enabled' if self.settings.get('auto_updates') else 'Disabled'}"""
            
            xbmcgui.Dialog().textviewer("Build Information", info_text)
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error showing build info - {str(e)}", xbmc.LOGERROR)

    def show_settings_menu(self):
        """Display settings menu"""
        try:
            menu_items = [
                "Device Settings",
                "Update Settings", 
                "Reset Wizard",
                "Export Settings",
                "Import Settings"
            ]
            
            choice = xbmcgui.Dialog().select("Settings", menu_items)
            
            if choice == -1:
                return
            elif choice == 0:  # Device Settings
                self.show_device_settings()
            elif choice == 1:  # Update Settings
                self.show_update_settings()
            elif choice == 2:  # Reset Wizard
                self.reset_wizard()
            elif choice == 3:  # Export Settings
                self.export_settings()
            elif choice == 4:  # Import Settings
                self.import_settings()
                
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error in settings menu - {str(e)}", xbmc.LOGERROR)

    def show_device_settings(self):
        """Show device-specific settings"""
        try:
            # Device name
            current_name = self.settings.get('device_name', '')
            new_name = xbmcgui.Dialog().input("Device Name", 
                                            "Enter device name (max 15 characters):",
                                            defaultt=current_name,
                                            type=xbmcgui.INPUT_ALPHANUM)
            if new_name is not None:
                self.settings['device_name'] = new_name[:15]
            
            # Audio channels
            current_audio = self.settings.get('audio_channels', '2.0')
            audio_options = ['2.0 (Stereo)', '5.1 (Surround)', '7.1 (Full Surround)']
            audio_values = ['2.0', '5.1', '7.1']
            
            try:
                current_index = audio_values.index(current_audio)
            except:
                current_index = 0
            
            audio_choice = xbmcgui.Dialog().select("Audio Channels", audio_options, preselect=current_index)
            if audio_choice >= 0:
                self.settings['audio_channels'] = audio_values[audio_choice]
            
            # Zip code
            current_zip = self.settings.get('zip_code', '')
            new_zip = xbmcgui.Dialog().input("Weather Location", 
                                           "Enter zip code for weather updates:",
                                           defaultt=current_zip,
                                           type=xbmcgui.INPUT_NUMERIC)
            if new_zip is not None:
                self.settings['zip_code'] = new_zip
            
            # Save settings
            self.save_settings()
            xbmcgui.Dialog().ok("Settings Saved", "Device settings have been updated.")
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error in device settings - {str(e)}", xbmc.LOGERROR)

    def show_update_settings(self):
        """Show update-related settings"""
        try:
            # Auto updates toggle
            auto_updates = xbmcgui.Dialog().yesno("Auto Updates", 
                                                "Enable automatic build updates?",
                                                nolabel="Disable",
                                                yeslabel="Enable")
            self.settings['auto_updates'] = auto_updates
            
            # Save settings
            self.save_settings()
            
            status = "enabled" if auto_updates else "disabled"
            xbmcgui.Dialog().ok("Settings Saved", f"Automatic updates {status}.")
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error in update settings - {str(e)}", xbmc.LOGERROR)

    def reset_wizard(self):
        """Reset wizard to factory defaults"""
        try:
            if xbmcgui.Dialog().yesno("Reset Wizard", 
                                    "This will reset all wizard settings and data.\nBuilds and backups will not be affected.\n\nContinue?"):
                
                # Reset settings to defaults
                self.settings = {
                    'first_run_complete': False,
                    'subtitles_enabled': True,
                    'lyrics_auto_display': True,
                    'device_name': '',
                    'zip_code': '',
                    'audio_channels': '2.0',
                    'last_update_check': 0,
                    'auto_updates': True,
                    'current_build': None,
                    'wizard_version': '1.0.0'
                }
                
                # Save reset settings
                self.save_settings()
                
                xbmcgui.Dialog().ok("Reset Complete", "Wizard has been reset to factory defaults.")
                
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error resetting wizard - {str(e)}", xbmc.LOGERROR)

    def export_settings(self):
        """Export wizard settings to file"""
        try:
            export_data = {
                'settings': self.settings,
                'build_info': self.build_info,
                'export_date': int(time.time())
            }
            
            export_file = os.path.join(self.addon_data_path, 'cutcable_settings_export.json')
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
            
            xbmcgui.Dialog().ok("Export Complete", f"Settings exported to:\n{export_file}")
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error exporting settings - {str(e)}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok("Export Failed", f"Could not export settings: {str(e)}")

    def import_settings(self):
        """Import wizard settings from file"""
        try:
            import_file = os.path.join(self.addon_data_path, 'cutcable_settings_export.json')
            
            if not os.path.exists(import_file):
                xbmcgui.Dialog().ok("Import Failed", "No settings export file found.")
                return
            
            if xbmcgui.Dialog().yesno("Import Settings", 
                                    "Import settings from export file?\nThis will overwrite current settings."):
                
                with open(import_file, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)
                
                if 'settings' in import_data:
                    self.settings.update(import_data['settings'])
                    self.save_settings()
                
                if 'build_info' in import_data:
                    self.build_info.update(import_data['build_info'])
                    with open(self.build_info_file, 'w', encoding='utf-8') as f:
                        json.dump(self.build_info, f, indent=2)
                
                xbmcgui.Dialog().ok("Import Complete", "Settings imported successfully.")
                
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error importing settings - {str(e)}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok("Import Failed", f"Could not import settings: {str(e)}")

    def show_about(self):
        """Display about information"""
        about_text = """CutCable Wizard v1.0.0

A comprehensive build management system for Kodi, optimized for Fire TV devices.

Features:
• Automatic build installation and updates
• User settings backup and restore
• Maintenance tools integration
• Fire TV optimized interface
• Secure admin build access

Created by: FrugalITDad
Repository: github.com/FrugalITDad/FrugalITDad

For support and updates, visit the GitHub repository."""

        xbmcgui.Dialog().textviewer("About CutCable Wizard", about_text)

    # Background service methods

    def startup_update_check(self):
        """Perform startup update check"""
        try:
            if not self.settings.get('auto_updates', True):
                return
            
            xbmc.log("CutCable Wizard: Performing startup update check", xbmc.LOGDEBUG)
            
            # Check for wizard updates
            wizard_updated = self.check_wizard_update()
            
            if not wizard_updated:
                # Check for build updates
                build_update = self.check_build_updates()
                if build_update:
                    # Install update silently
                    self.install_build(build_update)
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error in startup update check - {str(e)}", xbmc.LOGERROR)

    def periodic_update_check(self):
        """Perform periodic update check"""
        try:
            if not self.settings.get('auto_updates', True):
                return
            
            current_time = int(time.time())
            last_check = self.settings.get('last_update_check', 0)
            
            # Check once per day
            if current_time - last_check < 86400:
                return
            
            xbmc.log("CutCable Wizard: Performing periodic update check", xbmc.LOGDEBUG)
            
            # Update last check time
            self.settings['last_update_check'] = current_time
            self.save_settings()
            
            # Check for updates
            wizard_updated = self.check_wizard_update()
            
            if not wizard_updated:
                build_update = self.check_build_updates()
                if build_update:
                    # Show notification about available update
                    xbmc.executebuiltin('Notification(CutCable Wizard, Build update available, 5000)')
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error in periodic update check - {str(e)}", xbmc.LOGERROR)

    def check_wizard_update(self):
        """Check for wizard updates"""
        try:
            # Fetch latest addon.xml from repository
            addon_xml_url = f"{self.repo_base_url}plugin.program.cutcable.wizard/addon.xml"
            response = requests.get(addon_xml_url, timeout=self.request_timeout)
            
            if response.status_code == 200:
                # Parse version from addon.xml
                import re
                version_match = re.search(r'version="([^"]+)"', response.text)
                if version_match:
                    remote_version = version_match.group(1)
                    current_version = self.addon.getAddonInfo('version')
                    
                    if self.compare_versions(remote_version, current_version) > 0:
                        # Update available - let Kodi handle addon updates
                        xbmc.executebuiltin('UpdateAddonRepos')
                        return True
            
            return False
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error checking wizard update - {str(e)}", xbmc.LOGERROR)
            return False

    def check_build_updates(self):
        """Check for build updates"""
        try:
            current_build = self.build_info.get('installed_build')
            if not current_build:
                return None
            
            builds_data = self.fetch_builds_list()
            if not builds_data:
                return None
            
            # Find current build in list
            for build in builds_data.get('builds', []):
                if build['name'] == current_build:
                    remote_version = self.extract_version_from_name(build['name'])
                    current_version = self.build_info.get('version', '1.0')
                    
                    if self.compare_versions(remote_version, current_version) > 0:
                        return build
            
            return None
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error checking build updates - {str(e)}", xbmc.LOGERROR)
            return None

    def cleanup(self):
        """Cleanup method called before service shutdown"""
        try:
            # Clean up any temporary files
            self.cleanup_temp_files([])
            
            # Force garbage collection
            gc.collect()
            
            xbmc.log("CutCable Wizard: Service cleanup completed", xbmc.LOGDEBUG)
            
        except Exception as e:
            xbmc.log(f"CutCable Wizard: Error in cleanup - {str(e)}", xbmc.LOGERROR)
                
