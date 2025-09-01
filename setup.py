from setuptools import setup

APP = ['main_app.py']
OPTIONS = {
    'argv_emulation': True,
    'packages': ['tkinter', 'PIL'],
    'includes': ['PIL._imaging'],
    'site_packages': True,  # Include all site-packages
    'bundle_files': 1,      # Bundle everything into the app
    'plist': {
        'CFBundleName': 'Keyframe Curator',
        'CFBundleDisplayName': 'Keyframe Curator', 
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': True,
    }
}

setup(
    app=APP,
    name='Keyframe Curator',
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)