# INFO 4240 Grading Tools
Tools for grading from GradeScope.

### Requirements
Pandas, Python 3.6+
Optionally, you might install a jupyter notebook environment and open the example.

### How to
1. Ensure you have a rubric for the GradeScope assignment in question, as JSON. See examples in rubrics directory.
2. Download CSVs from "Export Evaluations" in GradeScope for that assignment. Rename directory to data. Place directory in this scripts folder.
3. Open grades.py. Replace rubric_path and csv_dir at the top. Run script from command line.

### Extra
If you have a different python running, you can create a python 3.6+ virtualenv in the directory, activate, then

```
  > virtualenv venv
  > source venv/bin/activate
  > pip install -r requirements.txt
```

Follow the steps as above but for a virtualenv. 
