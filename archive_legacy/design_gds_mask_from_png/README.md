In order to be able to use the script you must make a virtual env and install a few modules. Namely

1. Make a virtual environment with python3 :

```
python3 -m venv /Users/emilesoutter/Work/MainProject/Projects/2024/aws_sunda_2024_design_pgw/design_gds_mask/virtual_gdstk
```

Replace the absolute path `/Users/emilesoutter/Work/MainProject/Projects/2024/aws_sunda_2024_design_pgw/` by something appropriate.

2. Activate the venv:

```
source virtual_gdstk/bin/activate
```

3. Use `pip3` to install relevant modules:

```
pip3 install gdstk
pip3 install colorama
pip3 install opencv-python
```

4. Now use the script to generate design with commands such as:

```
 python3 obtain_gds_mask.py design.png
```
