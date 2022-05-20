import json
import pandas as pd
from collections import Counter


MIMIC_DIR = "path/to/MIMIC/Dir"
desc_json_path = "/path/to/icd/graph.json" # as presented in the CoPHE repo.


def initial_setup(desc_json_path):
    """
    Initialises a dataframe of relevant codes linked with their parent and grandparent codes
    """
    # loading the code description graph
    with open(desc_json_path, "r") as json_file:
        original_code_dict  = json.load(json_file)
        
    considered_labels = []
    for key in original_code_dict:
    	# Filtering grandparent/lower-deph entries
        if original_code_dict[key]["parents"][2]!=key:
            considered_labels.append(key)
    key_level = []
    parent_level = []
    grandparent_level = []
        
    for code in considered_labels:
        key_level.append(code)
        parent_level.append(original_code_dict[code]["parents"][0])
        grandparent_level.append(original_code_dict[code]["parents"][1])
    
    col_dict = dict({"code":key_level, "parent":parent_level, "grandparent":grandparent_level})
    code_df = pd.DataFrame(col_dict)
    
    return setup_sets(code_df, original_code_dict, considered_labels)


def accumulate_family(gp_code, df, valid_codes):
    """
    Given a grandparent code, the conversion dataframe, and a list of valid codes considered for your setup, creates a list of all the valid codes descended from the grandparent (including parents and leaves).
    """
    codes = []
    rows = df[df["grandparent"]==gp_code]
    for code in rows["code"]:
        if code in valid_codes:
            codes.append(code)
    return codes


def accumulate_siblings(p_code, df, valid_codes):
    """
    Given a parent code, the conversion dataframe, and a list of valid codes considered for your setup, creates a list of all the valid codes descended from the parent
    """
    codes = []
    rows = df[df["parent"]==p_code]
    for code in rows["code"]:
        if code in valid_codes:
            codes.append(code)
    return codes


def isolate_unspecified(codes, code_dict):
    """
    Given a list of codes and the code description graph isolates the codes with ``unspecified'' in the label description.
    """
    results = [code for code in codes if "unspecified" in code_dict[code]['label'].lower()]    
    return "|".join(results)


def isolate_other(codes, code_dict):
    """
    Given a list of codes and the code description graph isolates the non-``unspecified codes'' with ``other'' in the label description.
    """
    candidates = list(set(codes).difference(set(isolate_unspecified(codes, code_dict).split("|"))))
    results = [code for code in candidates if "other" in code_dict[code]['label'].lower()]    
    return "|".join(results)


def isolate_specified(codes, unspecified):
    """
    Given a list of codes and and the ``unspeciefied''s, returns the codes that are not ``unspecified''.
    """
    results = list(set(codes).difference(unspecified))
    return "|".join(results)


def create_conversion(row):
    """
    Providing the relevant labels for conversion -- if the input is parent level -- single-digit-etiology (e.g., 401.9) 
    """
    if row["code"]==row["parent"]:
        conversion = row["family_all"]
    else:
        conversion = row["siblings"]
    return conversion


def setup_sets(df, original_code_dict, valid_codes):
    """
    Takes all the accumlator and isolator methods, populates their respective dataframe columns
    """
    df["family_all"] = df.apply(lambda row: accumulate_family(row.grandparent, df, valid_codes), axis=1)
    df["siblings"] = df.apply(lambda row: accumulate_siblings(row.parent, df, valid_codes), axis=1)
    df["family"] = df.apply(create_conversion, axis=1)
    df["unspecified"] = df.apply(lambda row: isolate_unspecified(row.family, original_code_dict), axis = 1)
    df["other"] = df.apply(lambda row: isolate_other(row.family, original_code_dict), axis = 1)
    df["specified"] = df.apply(lambda row: isolate_specified(row.family, row.unspecified+row.other), axis = 1)
    return df

def derive_sets(MIMIC_DIR):
    """
    Used to determine the frequent, few-shot, and zero-shot codesets in Mullenbach's split of MIMIC-III
    The frequent set consists of codes appearing more than 5 times in the training set;
    The few-shot set consists of codes appearing at most 5 times, but at least once in the training set;
    The zero-shot set consists of codes appearing in MIMIC-III's discharge summaries, but not in the training set.
    """
    trainf = MIMIC_DIR + "/train_full.csv"
    devf = MIMIC_DIR + "/dev_full.csv"
    testf = MIMIC_DIR + "/test_full.csv"

    tr = pd.read_csv(trainf, converters={'LABELS': str})
    de = pd.read_csv(devf, converters={'LABELS': str})
    te = pd.read_csv(testf, converters={'LABELS': str})

    tr_labels = ";".join(list(tr.LABELS)).split(";")
    de_labels = ";".join(list(de.LABELS)).split(";")
    te_labels = ";".join(list(te.LABELS)).split(";")

    ctr = Counter(tr_labels)
    cde = Counter(de_labels)
    cte = Counter(te_labels)
    
    seen_set = set()
    few_shot = set()
    normal = set()
    for key in ctr.keys():
        if ctr[key]>5:
            normal.add(key)
        else:
            few_shot.add(key)
    seen_set = few_shot.union(normal)

    zero_shot = set(cte.keys()).union(set(cde.keys()))
    zero_shot = zero_shot.difference(seen_set)
    return normal, few_shot, zero_shot
    

def find_relevant_specifieds(frame, normal):
    """
    Finds relevant specified codes that are appearing in a code subset.
    """
    normal_frame = frame[frame["code"].isin(normal)]
    unspecifieds_list = list(normal_frame["unspecified"])

    unspecified_set = set()
    for l in unspecifieds_list:
        for code in l:
            unspecified_set.add(code)
    unspecified_set = unspecified_set.intersection(normal)

    unspecified_normals = normal_frame[normal_frame["code"].isin(unspecified_set)]

    specified_sets = list(unspecified_normals.specified)
    relevant_specifieds = set()
    for ss in specified_sets:
        relevant_specifieds=relevant_specifieds.union(ss)
    return relevant_specifieds, unspecified_normals, normal_frame
    

def filter_family_set(row, shot_set):
    """
    Given a row and a subset of codes, filter the row's specified candidate siblings by the subset.
    """
    return '|'.join(list(set(row.specified.split("|")).intersection(shot_set)))
    

def create_conversion_table(frame, norm, few, zero): 
    """
    Creates the final conversion table that allows the lookup: given a code, which viable siblings exist in the zero-shot, few-shot, and frequent subset respectively.
    """
    conversion_table= frame.copy()
    conversion_table["zero"]=conversion_table.apply(lambda row: filter_family_set(row, zero), axis=1)
    conversion_table["few"] = conversion_table.apply(lambda row: filter_family_set(row, few), axis=1)
    conversion_table["normal"]= conversion_table.apply(lambda row: filter_family_set(row, norm), axis=1)

    conversion_table = conversion_table.drop(columns=(["family_all", "siblings", "family"]))
    return conversion_table
    

def viable_sibling_check(df, code, subset):
    """
    Checks whether there is a viable sibling code for a code given the conversion table, and the code subset in which it should appear. 
    """
    assert subset in {"normal", "few", "zero"}
    options = set(df[df["code"]==code].iloc[0][subset])
    return len(options)>0
    

def random_sibling_code(df, code, subset):
    """
    Return a random viable sibiling given the conversion table, the code, and the subset in which the sibling is to appear.
    """
    assert subset in {"normal", "few", "zero"}
    options = set(df[df["code"]==code].iloc[0][subset])
    return choice(list(options))
    

def run_conversion_table(frame, MIMIC_DIR, conversion_path):
    """
    Bringing it all toghether
    """
    norm, few, zero = derive_sets(MIMIC_DIR)
    relevant_specified, unspecified_normal, nf = find_relevant_specifieds(frame, norm)        
    conversion_table = create_conversion_table(nf, norm, few, zero)
    conversion_table.to_csv(conversion_path)
    
if __name__ == "__main__":
    frame = initial_setup(desc_json_path)
    conversion_path = "/Path/where/to/save/conversion/table.csv"
    run_conversion_table(frame, MIMIC_DIR, conversion_path)
