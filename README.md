# Directory Tasks

Small tool to run recurring tasks defined in a directory on a background service.

My use case is to call recurring custom scripts (for example creating weekly note) on my obsidian vault independent of where the vault is edited (PC, Laptop, Tablet...). 
But there are many other ideas this could be used for:

- Automatically build PDF from typst or latex document every day
- Check for personal information, api keys or similar in files/documents on change
- Automatically rename files to adhere to some naming convention
- ...

## Usage

DirTasks is intendet to be run in a docker container (ideally on a NAS or a Server with access to the corresponding directory) but the python file can also be executed directly on the host system.

```
python main.py task_dir1 task_dir2 ...
```

The program expects a `.tasks` directory in the given directory with a `daily.py` (executed daily), `weekly.py` (executed weekly), `on_change` (executed on file change - with debounce). If a file is missing it will be skipped

Currently the execution time is fixed to 00:01:00 for the daily script and Mon (Or Sunday depending on you locale) 00:01:00. The debounce for the on change script is set to 10 minutes. If needed this can be changed at the top of the `main()` function in `main.py`

### Docker

I recommend to use docker compose. The docker compose file already present in the project can be used as a preset. By default only one directory is used but more directories can be added by updating the `command` property. 

> [!NOTE] 
> Always add the required directories as volumes
