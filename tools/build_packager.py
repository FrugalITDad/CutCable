#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CutCable Build Packager
Creates ZIP files for each build configuration from your Kodi setup
"""

import os
import shutil
import zipfile
import json
from datetime import datetime
import argparse

class CutCableBuildPackager:
    def __init__(self, kodi_userdata_path, output_dir):
        self.kodi_userdata = kodi_userdata_path
        self.output_dir = output_dir
        self.temp_dir = os.path.join(output_dir, 'temp')
        
        # Build configurations
        self.builds = {
            'CutCable': {
                'name': 'CutCable',
                'description': 'Basic CutCable build',
                'exclude_addons': [],  # Add addon IDs to exclude
                'include_extras': []   # Add extra files/folders
            },
            'CutCable-Plex': {
                'name': 'CutCable + Plex',
                'description': 'CutCable with Plex integration',
                'exclude_addons': [],
                'include_extras': ['plex_config.xml']  # Example
            },
            'CutCable-Games': {
                'name': 'CutCable + Games',
                'description': 'CutCable with gaming add-ons',
                'exclude_addons': [],
                'include_extras': ['games_config/']
            },
            'CutCable-Plex-Games': {
                'name': 'CutCable + Plex & Games', 
                'description': 'Full featured build',
                'exclude_addons': [],
                'include_extras': ['plex_config.xml', 'games_config/']
            },
            'CutCableAdmin': {
                'name': 'CutCableAdmin',
                'description': 'Admin build with advanced features',
                'exclude_addons': [],
                'include_extras': ['admin_tools/']
            },
            'CutCableAdmin-Games': {
                'name': 'CutCableAdmin + Games',
                'description': 'Admin build with gaming',
                'exclude_addons': [],
                'include_extras': ['admin_tools/', 'games_config/']
            }
        }
    
    def create_all_builds(self, version):
        """Create all build ZIP files"""
        print(f"Creating CutCable builds version {version}")
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create each build
        for build_key, build_config in self.builds.items():
            print(f"\nCreating {build_config['name']}...")
            self.create_build(build_key, build_config, version)
        
        print(f"\nAll builds created in: {self.output_dir}")
    
    def create_build(self, build_key, build_config, version):
        """Create a single build ZIP file"""
        try:
            # Create temporary build directory
            build_temp = os.path.join(self.temp_dir, build_key)
            if os.path.exists(build_temp):
                shutil.rmtree(build_temp)
            os.makedirs(build_temp)
            
            # Copy base Kodi configuration
            self.copy_base_config(build_temp, build_config)
            
            # Create build info file
            self.create_build_info(build_temp, build_key, build_config, version)
            
            # Create ZIP file
            zip_filename = f"{build_key}-v{version}.zip"
            zip_path = os.path.join(self.output_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(build_temp):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_path = os.path.relpath(file_path, build_temp)
                        zipf.write(file_path, arc_path)
            
            print(f"  Created: {zip_filename}")
            
            # Clean up temp directory
            shutil.rmtree(build_temp)
            
        except Exception as e:
            print(f"  ERROR creating {build_key}: {str(e)}")
    
    def copy_base_config(self, build_temp, build_config):
        """Copy base Kodi configuration to build directory"""
        
        # Essential directories to include in all builds
        essential_dirs = [
            'addon_data',
            'keymaps',
            'playlists'
        ]
        
        # Essential files
        essential_files = [
            'favourites.xml',
            'sources.xml',
            'advancedsettings.xml',
            'RssFeeds.xml',
            'profiles.xml'
        ]
        
        # Copy essential directories
        for dir_name in essential_dirs:
            src_dir = os.path.join(self.kodi_userdata, dir_name)
            if os.path.exists(src_dir):
                dst_dir = os.path.join(build_temp, dir_name)
                shutil.copytree(src_dir, dst_dir, ignore=self.get_ignore_patterns(build_config))
        
        # Copy essential files
        for file_name in essential_files:
            src_file = os.path.join(self.kodi_userdata, file_name)
            if os.path.exists(src_file):
                dst_file = os.path.join(build_temp, file_name)
                shutil.copy2(src_file, dst_file)
        
        # Copy addons directory (selective)
        self.copy_addons(build_temp, build_config)
        
        # Copy any extra files specified for this build
        for extra in build_config.get('include_extras', []):
            src_path = os.path.join(self.kodi_userdata, extra)
            if os.path.exists(src_path):
                dst_path = os.path.join(build_temp, extra)
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path)
                else:
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    shutil.copy2(src_path, dst_path)
    
    def copy_addons(self, build_temp, build_config):
        """Copy addons directory with exclusions"""
        addons_src = os.path.join(self.kodi_userdata, '../addons')
        addons_dst = os.path.join(build_temp, 'addons')
        
        if not os.path.exists(addons_src):
            return
        
        os.makedirs(addons_dst, exist_ok=True)
        
        # Get list of addons to exclude
        exclude_addons = set(build_config.get('exclude_addons', []))
        
        # Copy each addon directory
        for addon_name in os.listdir(addons_src):
            addon_src_path = os.path.join(addons_src, addon_name)
            
            # Skip if not a directory or if excluded
            if not os.path.isdir(addon_src_path) or addon_name in exclude_addons:
                continue
            
            addon_dst_path = os.path.join(addons_dst, addon_name)
            shutil.copytree(addon_src_path, addon_dst_path)
    
    def get_ignore_patterns(self, build_config):
        """Get ignore patterns for file copying"""
        def ignore_func(dir_path, names):
            ignored = []
            for name in names:
                # Skip temporary files
                if name.endswith('.tmp') or name.endswith('.bak'):
                    ignored.append(name)
                # Skip cache directories
                elif name in ['cache', 'temp', 'thumbnails']:
                    ignored.append(name)
            return ignored
        
        return ignore_func
    
    def create_build_info(self, build_temp, build_key, build_config, version):
        """Create build information file"""
        build_info = {
            'build_name': build_config['name'],
            'build_key': build_key,
            'description': build_config['description'],
            'version': version,
            'created_date': datetime.now().isoformat(),
            'creator': 'FrugalITDad',
            'kodi_version': 'Matrix/Nexus/Omega Compatible'
        }
        
        info_file = os.path.join(build_temp, 'cutcable_build_info.json')
        with open(info_file, 'w') as f:
            json.dump(build_info, f, indent=2)
    
    def cleanup(self):
        """Clean up temporary files"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

def main():
    parser = argparse.ArgumentParser(description='Create CutCable Kodi builds')
    parser.add_argument('--kodi-path', required=True, 
                       help='Path to Kodi userdata directory')
    parser.add_argument('--output', default='./builds',
                       help='Output directory for build files')
    parser.add_argument('--version', required=True,
                       help='Version number for builds (e.g., 1.0)')
    
    args = parser.parse_args()
    
    # Validate Kodi path
    if not os.path.exists(args.kodi_path):
        print(f"ERROR: Kodi userdata path not found: {args.kodi_path}")
        return 1
    
    # Create packager and build
    packager = CutCableBuildPackager(args.kodi_path, args.output)
    
    try:
        packager.create_all_builds(args.version)
        print("\nBuild creation completed successfully!")
        
        print("\nNext steps:")
        print("1. Test the builds by installing them")
        print("2. Upload the ZIP files to GitHub releases")
        print("3. Tag the release with the version number")
        
    except Exception as e:
        print(f"ERROR: Build creation failed - {str(e)}")
        return 1
    
    finally:
        packager.cleanup()
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())


# Example usage:
# python build_packager.py --kodi-path "C:\Users\YourName\AppData\Roaming\Kodi\userdata" --version 1.0
# python build_packager.py --kodi-path "/home/user/.kodi/userdata" --version 1.0
