"""Named complete settings snapshots and persistent provided-preset changes."""
import copy
import json
import os
from pathlib import Path
import tempfile
from file_safety import file_lock


ORIGINAL_GAME = 'Original Game'


def protected(name):
    return isinstance(name,str) and name.strip().casefold()==ORIGINAL_GAME.casefold()


def store_path():
    from preferences import preferences_path
    return preferences_path().with_name('custom-presets.json')


def preset_name(name):
    if not isinstance(name,str):raise ValueError('Enter a preset name.')
    name=name.strip()
    if not name or len(name)>60 or any(ord(c)<32 for c in name):
        raise ValueError('Use a preset name of 1–60 characters.')
    return name


def export_filename(name=None):
    """Suggest a single Windows-safe ROM filename without changing preset names."""
    if not isinstance(name,str)or not name.strip():return 'New Horizons Modified.sfc'
    stem=''.join('_'if c in '<>:"/\\|?*'or ord(c)<32 else c for c in name).strip().rstrip('. ')
    if stem.lower().endswith('.sfc'):stem=stem[:-4].rstrip('. ')
    if not stem:return 'New Horizons Modified.sfc'
    reserved={'CON','PRN','AUX','NUL'}|{prefix+suffix for prefix in ('COM','LPT')for suffix in '123456789¹²³'}
    if stem.split('.')[0].rstrip(' ').upper()in reserved:stem='_'+stem
    return stem+'.sfc'


def description(value):
    if not isinstance(value,str)or len(value)>2000 or any(ord(c)<32 and c not in '\n\t'for c in value):
        raise ValueError('Description must be text of at most 2,000 characters.')
    return value


class PresetStore:
    def __init__(self,path=None):self.path=Path(path)if path is not None else store_path()

    def _document(self):
        if not self.path.exists():return dict(presets={},deleted=[],descriptions={})
        try:
            data=json.loads(self.path.read_text(encoding='utf-8'))
            return self._validate_document(data)
        except (ValueError,UnicodeError)as error:
            raise ValueError('Custom presets could not be read. The existing file has been preserved.')from error

    @staticmethod
    def _validate_document(data):
        if not isinstance(data,dict)or data.get('format')!='new-horizons-custom-presets'or type(data.get('version'))is not int or data['version']not in (1,2,3)or set(data)!=({'format','version','presets'}if data['version']==1 else {'format','version','presets','deleted'}if data['version']==2 else {'format','version','presets','deleted','descriptions'})or not isinstance(data['presets'],dict):raise ValueError()
        deleted=data.get('deleted',[])
        if not isinstance(deleted,list)or any(not isinstance(n,str)or preset_name(n)!=n for n in deleted)or len(set(deleted))!=len(deleted):raise ValueError()
        for name,manifest in data['presets'].items():
            if preset_name(name)!=name or not isinstance(manifest,dict):raise ValueError()
        if len({n.casefold()for n in data['presets']})!=len(data['presets']):raise ValueError()
        descriptions=data.get('descriptions',{})
        if not isinstance(descriptions,dict)or any(name not in data['presets']or description(value)!=value for name,value in descriptions.items()):raise ValueError()
        return dict(presets=data['presets'],deleted=deleted,descriptions=descriptions)

    def _lock(self):
        return file_lock(self.path.with_suffix(self.path.suffix+'.lock'),resource='presets')

    def read(self):return self._document()['presets']

    def deleted(self):return self._document()['deleted']

    def descriptions(self):return self._document()['descriptions']

    def _write(self,presets,deleted,descriptions):
        # Callers hold the shared lock and supply one consistent document.
        document=dict(format='new-horizons-custom-presets',version=3,presets=presets,deleted=deleted,descriptions=descriptions)
        self._validate_document(document)
        self.path.parent.mkdir(parents=True,exist_ok=True);temporary=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=self.path.parent,delete=False)as file:
                temporary=Path(file.name)
                json.dump(document,file,indent=2)
                file.write('\n');file.flush();os.fsync(file.fileno())
            os.replace(temporary,self.path)
        finally:
            if temporary is not None:temporary.unlink(missing_ok=True)

    def save(self,name,project,replace=False,description_text=None):
        name=preset_name(name)
        if protected(name):raise ValueError('Original Game cannot be overwritten. Save your edits as a new preset.')
        if description_text is not None:description(description_text)
        # Expensive ROM validation precedes locking; re-read storage afterward.
        manifest=project.manifest();prepare(project,manifest)
        with self._lock():
            document=self._document();data=document['presets'];descriptions=document['descriptions']
            existing=next((n for n in data if n.casefold()==name.casefold()),None)
            if existing is not None and not replace:raise ValueError('A preset with that name already exists.')
            text=descriptions.get(existing,'')if description_text is None else description_text
            if existing is not None:del data[existing];descriptions.pop(existing,None)
            data[name]=manifest;descriptions[name]=text
            self._write(data,document['deleted'],descriptions)
        return name

    def delete(self,name,provided=False):
        if protected(name):raise ValueError('Original Game cannot be deleted.')
        from app_defaults import provided_names
        canonical=next((n for n in provided_names() if n.casefold()==name.casefold()),None)
        if provided and canonical is None:raise ValueError('That preset no longer exists.')
        with self._lock():
            document=self._document();data=document['presets'];deleted=document['deleted']
            if not provided:
                if name not in data:raise ValueError('That custom preset no longer exists.')
                del data[name]
            if canonical is not None and canonical not in deleted:deleted.append(canonical)
            self._write(data,deleted,{key:value for key,value in document['descriptions'].items()if key in data})

    def restore_provided(self):
        from app_defaults import provided_names
        names={name.casefold()for name in provided_names()}
        with self._lock():
            document=self._document()
            data={name:value for name,value in document['presets'].items()if name.casefold()not in names}
            self._write(data,[name for name in document['deleted']if name.casefold()not in names],{key:value for key,value in document['descriptions'].items()if key in data})


def prepare(project,manifest):
    """Validate the complete snapshot and ROM build on a detached candidate."""
    candidate=copy.deepcopy(project)
    candidate.load_manifest(manifest)
    candidate.build()
    return candidate


MANUAL_EDIT_FLAGS = ('custom_ships', 'custom_mates', 'custom_captains',
                     'custom_characters', 'custom_goods', 'custom_economy',
                     'custom_items', 'custom_discoveries')


def lock_manual_controls(project):
    """Loading a preset applies its values without unlocking manual editors."""
    for flag in MANUAL_EDIT_FLAGS:
        setattr(project, flag, False)
    return project


def starter(project,name,seed='0000',blind=False):
    """Return a validated bundled snapshot, independent of current edits."""
    from app_defaults import new_project, preset_document
    from backend import ShipProject
    if name==ORIGINAL_GAME:return ShipProject(project.source)
    bundled=preset_document()['presets']
    if name in bundled:
        candidate=ShipProject(project.source)
        candidate.load_manifest(bundled[name])
    elif name=='Full Randomizer':
        from easy_presets import apply
        candidate=new_project(project.source)
        apply(candidate,name,seed,blind)
    else:raise ValueError('Choose a preset.')
    candidate.build()
    return lock_manual_controls(candidate)


def apply_snapshot(project,candidate):
    # Preserve the active ROM and project destination, even if changed after review.
    settings=copy.deepcopy(candidate.__dict__)
    for key in ('source','project_path'):settings[key]=getattr(project,key)
    project.__dict__.update(settings)


def summary(project,candidate):
    from preset_changes import changes
    return changes(project,candidate)
