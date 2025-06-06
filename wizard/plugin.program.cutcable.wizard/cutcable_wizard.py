import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
import os
import json
import urllib.request
import zipfile
import shutil
from datetime import datetime

class CutCableWizard:
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.addon_path = self.addon.getAddonInfo('path')
        self.userdata_path = xbmcvfs.translatePath('special://userdata/')
        self.settings_file = os.path.join(self.userdata_path, 'cutcable_settings.json')
        self.backup_path = os.path.join(self.userdata_path, 'cutcable_backup')

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

    def _github_latest_release(self):
        """Helper to get latest release JSON from GitHub API"""
        try:
            with urllib.request.urlopen(f'{self.github_api}/releases/latest') as response:
                return json.load(response)
        except Exception as e:
            xbmc.log(f'CutCable Wizard: Failed to fetch latest release - {str(e)}', xbmc.LOGERROR)
            return None

    def show_main_menu(self):
        """Display the main wizard menu"""
        dialog = xbmcgui.Dialog()

        if not xbmcvfs.exists(self.settings_file):
            if dialog.yesno('CutCable Wizard', 'Welcome to CutCable Wizard!\n\nThis appears to be your first run.\nWould you like to install a build?'):
                self.show_build_selection()
            return

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
            self.show_admin_menu()  # <-- Unchanged per request

    def show_build_selection(self):
        """Display build selection menu"""
        dialog = xbmcgui.Dialog()
        public_builds = [build for build in self.builds.values() if not build['admin']]
        build_names = [f"{build['name']} - {build['description']}" for build in public_builds]

        choice = dialog.select('Select Build to Install', build_names)

        if choice >= 0:
            # Get public build keys in same order as build_names
            public_keys = [key for key, build in self.builds.items() if not build['admin']]
            selected_build = public_keys[choice]
            self.install_build(selected_build)

    def collect_user_settings(self):
        """Collect user settings during first installation"""
        dialog = xbmcgui.Dialog()
        settings = {}

        device_name = dialog.input('Enter Device Name (15 chars max):', type=xbmcgui.INPUT_ALPHANUM)
        if device_name:
            settings['device_name'] = device_name[:15]

        audio_options = ['2.0 Stereo', '2.1', '5.1', '7.1', 'Passthrough']
        audio_choice = dialog.select('Select Audio Channels:', audio_options)
        if audio_choice >= 0:
            settings['audio_channels'] = audio_options[audio_choice]

        subtitles = dialog.yesno('Subtitles', 'Enable subtitles by default?')
        settings['subtitles_enabled'] = subtitles

        zip_code = dialog.input('Enter Zip Code for Weather:', type=xbmcgui.INPUT_NUMERIC)
        if zip_code:
            settings['zip_code'] = zip_code

        lyrics = dialog.yesno('Music Lyrics', 'Display lyrics automatically?')
        settings['display_lyrics'] = lyrics

        self.save_user_settings(settings)
        return settings

    def save_user_settings(self, settings):
        """Save user settings to JSON file"""
        try:
            with xbmcvfs.File(self.settings_file, 'w') as f:
                f.write(json.dumps(settings, indent=2))
        except Exception as e:
            xbmc.log(f'CutCable Wizard: Error saving settings - {str(e)}', xbmc.LOGERROR)

    def load_user_settings(self):
        """Load user settings from JSON file"""
        try:
            if xbmcvfs.exists(self.settings_file):
                with xbmcvfs.File(self.settings_file, 'r') as f:
                    content = f.read()
                    return json.loads(content)
        except Exception as e:
            xbmc.log(f'CutCable Wizard: Error loading settings - {str(e)}', xbmc.LOGERROR)
        return {}

    def apply_user_settings(self, settings):
        """Apply user settings to Kodi"""
        try:
            if 'device_name' in settings:
                xbmc.executebuiltin(f'SetProperty(DeviceName,{settings["device_name"]},home)')

            if 'audio_channels' in settings:
                audio_map = {
                    '2.0 Stereo': '2.0',
                    '2.1': '2.1',
                    '5.1': '5.1',
                    '7.1': '7.1',
                    'Passthrough': 'passthrough'
                }
                audio_setting = audio_map.get(settings['audio_channels'], '2.0')
                xbmc.executebuiltin(f'SetSetting(audiooutput.channels,{audio_setting})')

            if 'subtitles_enabled' in settings:
                xbmc.executebuiltin(f'SetSetting(subtitles.show,{str(settings["subtitles_enabled"]).lower()})')

            if 'zip_code' in settings:
                try:
                    weather_addon = xbmcaddon.Addon('weather.gismeteo')
                    weather_addon.setSetting('Location', settings['zip_code'])
                except Exception:
                    pass  # Weather addon not installed

            if 'display_lyrics' in settings:
                try:
                    lyrics_addon = xbmcaddon.Addon('script.cu.lrclyrics')
                    lyrics_addon.setSetting('auto_show', str(settings['display_lyrics']).lower())
                except Exception:
                    pass  # Lyrics addon not installed
        except Exception as e:
            xbmc.log(f'CutCable Wizard: Error applying settings - {str(e)}', xbmc.LOGERROR)

    def create_backup(self):
        """Create backup of current Kodi configuration"""
        try:
            if not xbmcvfs.exists(self.backup_path):
                xbmcvfs.mkdir(self.backup_path)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_folder = os.path.join(self.backup_path, f'backup_{timestamp}')

            if not xbmcvfs.exists(backup_folder):
                xbmcvfs.mkdir(backup_folder)

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
                dst_path = os.path.join(backup_folder, item)
                if xbmcvfs.exists(src_path):
                    if xbmcvfs.isdir(src_path):
                        if not xbmcvfs.exists(dst_path):
                            shutil.copytree(src_path, dst_path)
                    else:
                        # Ensure parent folder exists
                        parent_dir = os.path.dirname(dst_path)
                        if not xbmcvfs.exists(parent_dir):
                            xbmcvfs.mkdir(parent_dir)
                        shutil.copy2(src_path, dst_path)

            return backup_folder
        except Exception as e:
            xbmc.log(f'CutCable Wizard: Backup failed - {str(e)}', xbmc.LOGERROR)
            return None

    def install_build(self, build_key):
        """Install selected build"""
        dialog = xbmcgui.Dialog()
        build = self.builds[build_key]

        if not dialog.yesno('Confirm Installation',
                           f'Install {build["name"]}?\n\n{build["description"]}\n\nThis will backup your current settings.'):
            return

        settings = self.load_user_settings()
        if not settings:
            settings = self.collect_user_settings()

        progress = xbmcgui.DialogProgress()
        progress.create('CutCable Wizard', 'Creating backup...')
        progress.update(10)

        backup_path = self.create_backup()
        if not backup_path:
            progress.close()
            dialog.ok('Error', 'Failed to create backup. Installation cancelled.')
            return

        progress.update(30, 'Downloading build...')

        if self.download_and_install_build(build_key, progress):
            progress.update(90, 'Applying settings...')
            self.apply_user_settings(settings)
            self.save_build_info(build_key)

            progress.update(100, 'Installation complete!')
            progress.close()

            dialog.ok('Success', f'{build["name"]} installed successfully!\n\nKodi will restart to complete installation.')
            xbmc.executebuiltin('RestartApp')
        else:
            progress.close()
            dialog.ok('Error', 'Installation failed. Your backup is preserved.')

    def download_and_install_build(self, build_key, progress):
        """Download and install build from GitHub with chunked progress"""
        try:
            build = self.builds[build_key]
            release_data = self._github_latest_release()
            if not release_data:
                return False

            build_asset = None
            for asset in release_data.get('assets', []):
                if asset['name'].startswith(build['file_prefix']):
                    build_asset = asset
                    break

            if not build_asset:
                xbmc.log(f'CutCable Wizard: Build file not found for {build_key}', xbmc.LOGERROR)
                return False

            download_url = build_asset['browser_download_url']
            build_file = os.path.join(self.userdata_path, 'temp_build.zip')

            progress.update(50, 'Downloading build file...')
            with urllib.request.urlopen(download_url) as response, open(build_file, 'wb') as out_file:
                file_size = int(response.getheader('Content-Length', '0'))
                downloaded = 0
                block_size = 8192
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    out_file.write(buffer)
                    downloaded += len(buffer)
                    if file_size > 0:
                        percent = 50 + int(40 * downloaded / file_size)
                        progress.update(percent, f'Downloading build file... {percent}%')

            progress.update(90, 'Installing build...')
            with zipfile.ZipFile(build_file, 'r') as zip_ref:
                zip_ref.extractall(self.userdata_path)

            os.remove(build_file)
            return True
        except Exception as e:
            xbmc.log(f'CutCable Wizard: Installation failed - {str(e)}', xbmc.LOGERROR)
            return False

    def save_build_info(self, build_key):
        """Save current build info to version file"""
        try:
            release_data = self._github_latest_release()
            if not release_data:
                return

            build_info = {
                'build_key': build_key,
                'build_name': self.builds[build_key]['name'],
                'version': release_data.get('tag_name', '1.0'),
                'installed_date': datetime.now().isoformat(),
                'last_check': datetime.now().isoformat()
            }

            with xbmcvfs.File(self.version_file, 'w') as f:
                f.write(json.dumps(build_info, indent=2))
        except Exception as e:
            xbmc.log(f'CutCable Wizard: Error saving build info - {str(e)}', xbmc.LOGERROR)

    def check_for_updates(self):
        """Check for updates to current build"""
        dialog = xbmcgui.Dialog()
        try:
            if not xbmcvfs.exists(self.version_file):
                dialog.ok('No Build Installed', 'No CutCable build detected.')
                return

            with xbmcvfs.File(self.version_file, 'r') as f:
                current_info = json.loads(f.read())

            release_data = self._github_latest_release()
            if not release_data:
                dialog.ok('Error', 'Failed to check for updates.')
                return

            latest_version = release_data.get('tag_name', '1.0')
            current_version = current_info.get('version', '1.0')

            if latest_version != current_version:
                if dialog.yesno('Update Available',
                               f'Update available!\n\nCurrent: v{current_version}\nLatest: v{latest_version}\n\nInstall update?'):
                    self.install_build(current_info['build_key'])
            else:
                dialog.ok('Up to Date', f'You have the latest version (v{current_version})')

            current_info['last_check'] = datetime.now().isoformat()
            with xbmcvfs.File(self.version_file, 'w') as f:
                f.write(json.dumps(current_info, indent=2))

        except Exception as e:
            xbmc.log(f'CutCable Wizard: Update check failed - {str(e)}', xbmc.LOGERROR)
            dialog.ok('Error', 'Failed to check for updates.')

    def startup_update_check(self):
        """Automatic update check on Kodi startup"""
        try:
            if not xbmcvfs.exists(self.version_file):
                return

            with xbmcvfs.File(self.version_file, 'r') as f:
                current_info = json.loads(f.read())

            last_check = datetime.fromisoformat(current_info.get('last_check', '2000-01-01T00:00:00'))
            now = datetime.now()

            if (now - last_check).days < 1:
                return

            release_data = self._github_latest_release()
            if not release_data:
                return

            latest_version = release_data.get('tag_name', '1.0')
            current_version = current_info.get('version', '1.0')

            if latest_version != current_version:
                dialog = xbmcgui.Dialog()
                if dialog.yesno('CutCable Update',
                               f'Update available for {current_info["build_name"]}!\n\nInstall now?',
                               nolabel='Later', yeslabel='Install'):
                    self.install_build(current_info['build_key'])

            current_info['last_check'] = now.isoformat()
            with xbmcvfs.File(self.version_file, 'w') as f:
                f.write(json.dumps(current_info, indent=2))

        except Exception as e:
            xbmc.log(f'CutCable Wizard: Startup update check failed - {str(e)}', xbmc.LOGERROR)

    # Keeping the show_admin_menu() unchanged per your request


# Main execution
if __name__ == '__main__':
    wizard = CutCableWizard()

    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'startup':
        wizard.startup_update_check()
    else:
        wizard.show_main_menu()
