import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
import os
import json
import urllib2
import zipfile
import shutil
from datetime import datetime

class CutCableWizard:
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.addon_path = self.addon.getAddonInfo('path')
        self.userdata_path = xbmc.translatePath('special://userdata/')
        self.settings_file = os.path.join(self.userdata_path, 'cutcable_settings.xml')
        self.backup_path = os.path.join(self.userdata_path, 'cutcable_backup/')
        
        # GitHub Configuration
        self.github_user = 'FrugalITDad'
        self.github_repo = 'FrugalITDad'
        self.github_api = f'https://api.github.com/repos/{self.github_user}/{self.github_repo}'
        
        # Build definitions
        self.builds = {
            'cutcable': {
                'name': 'CutCable',
                'description': 'Basic CutCable build with essential add-ons',
                'file_prefix': 'CutCable',
                'admin': False
            },
            'cutcable_plex': {
                'name': 'CutCable + Plex',
                'description': 'CutCable build with Plex integration',
                'file_prefix': 'CutCable-Plex',
                'admin': False
            },
            'cutcable_games': {
                'name': 'CutCable + Games',
                'description': 'CutCable build with gaming add-ons',
                'file_prefix': 'CutCable-Games',
                'admin': False
            },
            'cutcable_plex_games': {
                'name': 'CutCable + Plex & Games',
                'description': 'Full CutCable build with Plex and gaming',
                'file_prefix': 'CutCable-Plex-Games',
                'admin': False
            },
            'cutcable_admin': {
                'name': 'CutCableAdmin',
                'description': 'Admin build with advanced features',
                'file_prefix': 'CutCableAdmin',
                'admin': True
            },
            'cutcable_admin_games': {
                'name': 'CutCableAdmin + Games',
                'description': 'Admin build with gaming add-ons',
                'file_prefix': 'CutCableAdmin-Games',
                'admin': True
            }
        }
        
        # Current version tracking
        self.version_file = os.path.join(self.userdata_path, 'cutcable_version.json')
        
    def show_main_menu(self):
        """Display the main wizard menu"""
        dialog = xbmcgui.Dialog()
        
        # Check if this is first run
        if not os.path.exists(self.settings_file):
            if dialog.yesno('CutCable Wizard', 'Welcome to CutCable Wizard!\n\nThis appears to be your first run.\nWould you like to install a build?'):
                self.show_build_selection()
            return
        
        # Existing installation - show options
        options = [
            'Install/Change Build',
            'Update Current Build', 
            'Check for Updates',
            'Restore from Backup',
            'Admin Options'
        ]
        
        choice = dialog.select('CutCable Wizard - Main Menu', options)
        
        if choice == 0:
            self.show_build_selection()
        elif choice == 1:
            self.update_current_build()
        elif choice == 2:
            self.check_for_updates()
        elif choice == 3:
            self.restore_from_backup()
        elif choice == 4:
            self.show_admin_menu()
    
    def show_build_selection(self):
        """Display build selection menu"""
        dialog = xbmcgui.Dialog()
        
        # Show public builds
        public_builds = [build for build in self.builds.values() if not build['admin']]
        build_names = [f"{build['name']} - {build['description']}" for build in public_builds]
        
        choice = dialog.select('Select Build to Install', build_names)
        
        if choice >= 0:
            selected_build = list(self.builds.keys())[choice]
            self.install_build(selected_build)
    
    def show_admin_menu(self):
        """Show admin menu with password protection"""
        dialog = xbmcgui.Dialog()
        
        # Simple password prompt - you can change this password
        password = dialog.input('Enter Admin Password:', type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
        
        if password != 'FrugalAdmin2025':  # Change this password as needed
            dialog.ok('Access Denied', 'Incorrect password.')
            return
        
        # Show admin options
        options = [
            'Install Admin Builds',
            'Beta Channel Access',
            'Force Update Check',
            'View Debug Info',
            'Clear All Settings'
        ]
        
        choice = dialog.select('Admin Menu', options)
        
        if choice == 0:
            self.show_admin_builds()
        elif choice == 1:
            self.show_beta_builds()
        elif choice == 2:
            self.force_update_check()
        elif choice == 3:
            self.show_debug_info()
        elif choice == 4:
            self.clear_all_settings()
    
    def show_admin_builds(self):
        """Show admin-only builds"""
        dialog = xbmcgui.Dialog()
        
        admin_builds = [build for build in self.builds.values() if build['admin']]
        build_names = [f"{build['name']} - {build['description']}" for build in admin_builds]
        
        choice = dialog.select('Select Admin Build', build_names)
        
        if choice >= 0:
            # Find the corresponding build key
            admin_keys = [key for key, build in self.builds.items() if build['admin']]
            selected_build = admin_keys[choice]
            self.install_build(selected_build)
    
    def collect_user_settings(self):
        """Collect user settings during first installation"""
        dialog = xbmcgui.Dialog()
        settings = {}
        
        # Device Name (15 characters max)
        device_name = dialog.input('Enter Device Name (15 chars max):', type=xbmcgui.INPUT_ALPHANUM)
        if device_name:
            settings['device_name'] = device_name[:15]
        
        # Audio Channels
        audio_options = ['2.0 Stereo', '2.1', '5.1', '7.1', 'Passthrough']
        audio_choice = dialog.select('Select Audio Channels:', audio_options)
        if audio_choice >= 0:
            settings['audio_channels'] = audio_options[audio_choice]
        
        # Subtitles
        subtitles = dialog.yesno('Subtitles', 'Enable subtitles by default?')
        settings['subtitles_enabled'] = subtitles
        
        # Zip Code for Weather
        zip_code = dialog.input('Enter Zip Code for Weather:', type=xbmcgui.INPUT_NUMERIC)
        if zip_code:
            settings['zip_code'] = zip_code
        
        # Music Lyrics
        lyrics = dialog.yesno('Music Lyrics', 'Display lyrics automatically?')
        settings['display_lyrics'] = lyrics
        
        # Save settings
        self.save_user_settings(settings)
        return settings
    
    def save_user_settings(self, settings):
        """Save user settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            xbmc.log(f'CutCable Wizard: Error saving settings - {str(e)}', xbmc.LOGERROR)
    
    def load_user_settings(self):
        """Load user settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            xbmc.log(f'CutCable Wizard: Error loading settings - {str(e)}', xbmc.LOGERROR)
        return {}
    
    def apply_user_settings(self, settings):
        """Apply user settings to Kodi"""
        try:
            # Apply device name
            if 'device_name' in settings:
                xbmc.executebuiltin(f'SetProperty(DeviceName,{settings["device_name"]},home)')
            
            # Apply audio settings
            if 'audio_channels' in settings:
                # Map to Kodi audio settings
                audio_map = {
                    '2.0 Stereo': '2.0',
                    '2.1': '2.1', 
                    '5.1': '5.1',
                    '7.1': '7.1',
                    'Passthrough': 'passthrough'
                }
                audio_setting = audio_map.get(settings['audio_channels'], '2.0')
                xbmc.executebuiltin(f'SetSetting(audiooutput.channels,{audio_setting})')
            
            # Apply subtitle settings
            if 'subtitles_enabled' in settings:
                xbmc.executebuiltin(f'SetSetting(subtitles.show,{str(settings["subtitles_enabled"]).lower()})')
            
            # Configure weather add-on (Gismeteo)
            if 'zip_code' in settings:
                try:
                    weather_addon = xbmcaddon.Addon('weather.gismeteo')
                    weather_addon.setSetting('Location', settings['zip_code'])
                except:
                    pass  # Weather add-on not installed yet
            
            # Configure lyrics add-on (CU LRC Lyrics)  
            if 'display_lyrics' in settings:
                try:
                    lyrics_addon = xbmcaddon.Addon('script.cu.lrclyrics')
                    lyrics_addon.setSetting('auto_show', str(settings['display_lyrics']).lower())
                except:
                    pass  # Lyrics add-on not installed yet
                    
        except Exception as e:
            xbmc.log(f'CutCable Wizard: Error applying settings - {str(e)}', xbmc.LOGERROR)
    
    def create_backup(self):
        """Create backup of current Kodi configuration"""
        try:
            if not os.path.exists(self.backup_path):
                os.makedirs(self.backup_path)
            
            # Backup timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_folder = os.path.join(self.backup_path, f'backup_{timestamp}')
            os.makedirs(backup_folder)
            
            # Key folders to backup
            backup_items = [
                'addon_data',
                'keymaps', 
                'playlists',
                'userdata/favourites.xml',
                'userdata/advancedsettings.xml',
                'userdata/sources.xml'
            ]
            
            for item in backup_items:
                src_path = os.path.join(self.userdata_path, item)
                if os.path.exists(src_path):
                    dst_path = os.path.join(backup_folder, item)
                    if os.path.isdir(src_path):
                        shutil.copytree(src_path, dst_path)
                    else:
                        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                        shutil.copy2(src_path, dst_path)
            
            return backup_folder
            
        except Exception as e:
            xbmc.log(f'CutCable Wizard: Backup failed - {str(e)}', xbmc.LOGERROR)
            return None
    
    def install_build(self, build_key):
        """Install selected build"""
        dialog = xbmcgui.Dialog()
        build = self.builds[build_key]
        
        # Confirm installation
        if not dialog.yesno('Confirm Installation', 
                           f'Install {build["name"]}?\n\n{build["description"]}\n\nThis will backup your current settings.'):
            return
        
        # Collect user settings if first time
        settings = self.load_user_settings()
        if not settings:
            settings = self.collect_user_settings()
        
        # Create backup
        progress = xbmcgui.DialogProgress()
        progress.create('CutCable Wizard', 'Creating backup...')
        progress.update(10)
        
        backup_path = self.create_backup()
        if not backup_path:
            dialog.ok('Error', 'Failed to create backup. Installation cancelled.')
            return
        
        # Download and install build
        progress.update(30, 'Downloading build...')
        
        if self.download_and_install_build(build_key, progress):
            # Apply user settings
            progress.update(90, 'Applying settings...')
            self.apply_user_settings(settings)
            
            # Save current build info
            self.save_build_info(build_key)
            
            progress.update(100, 'Installation complete!')
            progress.close()
            
            dialog.ok('Success', f'{build["name"]} installed successfully!\n\nKodi will restart to complete installation.')
            xbmc.executebuiltin('RestartApp')
        else:
            progress.close()
            dialog.ok('Error', 'Installation failed. Your backup is preserved.')
    
    def download_and_install_build(self, build_key, progress):
        """Download and install build from GitHub"""
        try:
            build = self.builds[build_key]
            
            # Get latest release info
            releases_url = f'{self.github_api}/releases/latest'
            response = urllib2.urlopen(releases_url)
            release_data = json.loads(response.read())
            
            # Find the build file
            build_asset = None
            for asset in release_data.get('assets', []):
                if asset['name'].startswith(build['file_prefix']):
                    build_asset = asset
                    break
            
            if not build_asset:
                xbmc.log(f'CutCable Wizard: Build file not found for {build_key}', xbmc.LOGERROR)
                return False
            
            # Download build
            download_url = build_asset['browser_download_url']
            build_file = os.path.join(self.userdata_path, 'temp_build.zip')
            
            progress.update(50, 'Downloading build file...')
            
            # Simple download (you might want to add progress tracking)
            response = urllib2.urlopen(download_url)
            with open(build_file, 'wb') as f:
                f.write(response.read())
            
            # Extract build
            progress.update(70, 'Installing build...')
            
            with zipfile.ZipFile(build_file, 'r') as zip_ref:
                zip_ref.extractall(self.userdata_path)
            
            # Clean up
            os.remove(build_file)
            
            return True
            
        except Exception as e:
            xbmc.log(f'CutCable Wizard: Installation failed - {str(e)}', xbmc.LOGERROR)
            return False
    
    def save_build_info(self, build_key):
        """Save current build information"""
        try:
            # Get current version from GitHub
            releases_url = f'{self.github_api}/releases/latest'
            response = urllib2.urlopen(releases_url)
            release_data = json.loads(response.read())
            
            build_info = {
                'build_key': build_key,
                'build_name': self.builds[build_key]['name'],
                'version': release_data.get('tag_name', '1.0'),
                'installed_date': datetime.now().isoformat(),
                'last_check': datetime.now().isoformat()
            }
            
            with open(self.version_file, 'w') as f:
                json.dump(build_info, f, indent=2)
                
        except Exception as e:
            xbmc.log(f'CutCable Wizard: Error saving build info - {str(e)}', xbmc.LOGERROR)
    
    def check_for_updates(self):
        """Check for updates to current build"""
        try:
            if not os.path.exists(self.version_file):
                xbmcgui.Dialog().ok('No Build Installed', 'No CutCable build detected.')
                return
            
            with open(self.version_file, 'r') as f:
                current_info = json.load(f)
            
            # Check GitHub for latest version
            releases_url = f'{self.github_api}/releases/latest'
            response = urllib2.urlopen(releases_url)
            release_data = json.loads(response.read())
            
            latest_version = release_data.get('tag_name', '1.0')
            current_version = current_info.get('version', '1.0')
            
            if latest_version != current_version:
                dialog = xbmcgui.Dialog()
                if dialog.yesno('Update Available', 
                               f'Update available!\n\nCurrent: v{current_version}\nLatest: v{latest_version}\n\nInstall update?'):
                    self.install_build(current_info['build_key'])
            else:
                xbmcgui.Dialog().ok('Up to Date', f'You have the latest version (v{current_version})')
                
            # Update last check time
            current_info['last_check'] = datetime.now().isoformat()
            with open(self.version_file, 'w') as f:
                json.dump(current_info, f, indent=2)
                
        except Exception as e:
            xbmc.log(f'CutCable Wizard: Update check failed - {str(e)}', xbmc.LOGERROR)
            xbmcgui.Dialog().ok('Error', 'Failed to check for updates.')
    
    def startup_update_check(self):
        """Automatic update check on Kodi startup"""
        try:
            if not os.path.exists(self.version_file):
                return
            
            with open(self.version_file, 'r') as f:
                current_info = json.load(f)
            
            # Check if we should check for updates (don't spam)
            last_check = datetime.fromisoformat(current_info.get('last_check', '2000-01-01T00:00:00'))
            now = datetime.now()
            
            # Check at most once per day
            if (now - last_check).days < 1:
                return
            
            # Quick check for updates
            releases_url = f'{self.github_api}/releases/latest'
            response = urllib2.urlopen(releases_url)
            release_data = json.loads(response.read())
            
            latest_version = release_data.get('tag_name', '1.0')
            current_version = current_info.get('version', '1.0')
            
            if latest_version != current_version:
                dialog = xbmcgui.Dialog()
                if dialog.yesno('CutCable Update', 
                               f'Update available for {current_info["build_name"]}!\n\nInstall now?',
                               nolabel='Later', yeslabel='Install'):
                    self.install_build(current_info['build_key'])
            
            # Update last check time
            current_info['last_check'] = now.isoformat()
            with open(self.version_file, 'w') as f:
                json.dump(current_info, f, indent=2)
                
        except Exception as e:
            xbmc.log(f'CutCable Wizard: Startup update check failed - {str(e)}', xbmc.LOGERROR)

# Main execution
if __name__ == '__main__':
    wizard = CutCableWizard()
    
    # Check if this is a startup check
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'startup':
        wizard.startup_update_check()
    else:
        wizard.show_main_menu()
