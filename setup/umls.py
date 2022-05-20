from owlready2 import *
from owlready2.pymedtermino2 import *
from owlready2.pymedtermino2.umls import *

"""
Creates a pymedetermino world environment, populates it with entries from the ICD9CM, ICD10, SNOMEDCT_US and UMLS CUI.
Saves it as the "pym.sqlite3" file.
"""

if __name__ == "__main__":
    umls_path = "/path/to/umls/folder/"
    default_world.set_backend(filename = "pym.sqlite3")
    import_umls(umls_path+"umls-2021AA-full.zip", terminologies = ["ICD9CM", "ICD10", "SNOMEDCT_US", "CUI"])
    default_world.save()
