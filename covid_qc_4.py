from bs4 import BeautifulSoup
from selenium import webdriver
import re
import requests
import io
import pandas as pd 
import xlrd, xlwt
from pandas import ExcelWriter
from pandas import ExcelFile

URL = "https://www.quebec.ca/sante/problemes-de-sante/a-z/coronavirus-2019/situation-coronavirus-quebec/"
ID_1 = "#c63027" #div today cases / this week
ID_2 = "#c63029" #div today deaths
ID_3 = "#c50212" #div today under investigation
ID_4 = "#c50210" #div nombre d’hospitalisations
ID_5 = "c63047" #div Données cumulatives, date
ID_6 = "c70396" #last week

REGIONS = ["Bas-Saint-Laurent", "Saguenay – Lac-Saint-Jean", "Capitale-Nationale", "Mauricie-et-Centre-du-Québec", "Estrie", "Montréal", "Outaouais", "Abitibi-Témiscamingue", "Côte-Nord", "Nord-du-Québec", "Gaspésie – Îles-de-la-Madeleine", "Chaudière-Appalaches", "Laval", "Lanaudière", "Laurentides", "Montérégie", "Nunavik", "Terres-Cries-de-la-Baie-James", "Hors Québec", "Région à déterminer"]

def parse_page_initial(url, id_1, id_2, id_3, id_4, id_5):
    driver = webdriver.Chrome()
    driver.get(url)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()
    initial_case = soup.select(id_1)
    initial_deaths = soup.select(id_2)
    initial_investigation_number = soup.select(id_3)
    initial_hospitalisations = soup.select(id_4)
    data_cumulatives = soup.find("div", id = id_5).get_text()
    return initial_case, initial_deaths, initial_investigation_number, initial_hospitalisations, data_cumulatives

def remove_sub(data_dict, sub):
    for key in data_dict:
        if sub in data_dict[key]:
            data_dict[key] = data_dict[key].replace(sub, '')
    return data_dict

def dict_str_to_int(today_data_dict, date):
    total = 0
    for key in today_data_dict:
        if today_data_dict[key].isdigit():
            today_data_dict[key] = int(today_data_dict[key])
            total+=today_data_dict[key]
    today_data_dict['total'] = total
    today_data_dict['date'] = date

    return today_data_dict

def today_data_dict(today_data_list, date, sub_1, sub_2):
    region_index = 0
    today_data_dict = {}
    for region_data in today_data_list:
        region_len = len(REGIONS[region_index])
        region_data_len = (len(region_data)-2)
        if REGIONS[region_index] in region_data:
            today_data_dict[REGIONS[region_index]] = region_data[region_len:(region_data_len)]
        region_index+=1
    remove_sub(today_data_dict, sub_1)
    remove_sub(today_data_dict, sub_2)
    dict_str_to_int(today_data_dict, date)
    return today_data_dict

def append_terres_cries_data(today_data):
    Terres_Cries_initial = today_data[-1]
    Terres_Cries_final = Terres_Cries_initial.split('rs Québec')[0]
    append_data_terre_cries = [Terres_Cries_final]
    append_data_hors = ['Hors Québec{}'.format(Terres_Cries_initial.split('Hors Québec')[1].split('gion à déterminer')[0])]
    append_data_a_determiner = ['Région à déterminer{}'.format(Terres_Cries_initial.split('Hors Québec')[1].split('Région à déterminer')[1].split('tal')[0])]
    today_data_list = today_data[:-1] + append_data_terre_cries + append_data_hors + append_data_a_determiner
    return today_data_list

def excel_append(filename, dict_of_data):
    df_read = pd.read_excel(filename+".xlsx")
    df_new = df_read.append(dict_of_data, ignore_index = True)
    with pd.ExcelWriter(filename+".xlsx") as writer:
        df_new.to_excel(writer, index=False)

def update_data_file(filename, dict_of_data):
    filename_ext = filename+".txt"
    with open(filename_ext, "r", encoding = "utf-8") as f:
        if dict_of_data["date"] not in f.read():
            with open(filename_ext, "a", encoding = "utf-8") as f:
                f.write(dict_of_data["date"] + " ")
                f.write(str(dict_of_data))
                f.write("\n")
            #print("All write")
            excel_append(filename, dict_of_data)

def check_date(filename, tuple_of_dates):
    filename_ext = filename+".txt"
    with open(filename_ext, "r", encoding = "utf-8") as f:
        list_of_actual_dates = list()
        for date in tuple_of_dates:
            if date not in f.read():
                list_of_actual_dates.append(date)
    return list_of_actual_dates

def extract_number(row):
    index_start = row.find(">")
    number = row[index_start+1:-2]
    return number

def get_hospitalisation_dict(parse_initial_hospitalisation):
    initial_hospitalisation = str(parse_initial_hospitalisation)
    rows = initial_hospitalisation.split("li>")
    split_date = rows[6].split('es centres hospitaliers')[1].split()[2:5]
    date = " ".join(split_date)
    hospitalisation_dict = dict()
    hospitalisation_dict["date"] = date
    hospitalisation_keys = ["Nombre d’hospitalisations régulières", "Nombre en soins intensifs", "Nombre total d'hospitalisations"]
    rows_utiles = [1, 3, 5]
    for row in enumerate(rows_utiles):
        hospitalisation_dict[hospitalisation_keys[row[0]]] = int(rows[row[1]].split()[-1][:-2])
    # print(hospitalisation_dict)
    return hospitalisation_dict, date


def get_deaths_dict(parse_initial_deaths):
    initial_deaths = str(parse_initial_deaths).replace('\xa0', '')
    rows = initial_deaths.split("tr>")
    rows_clean=list()
    for row_number in range(3, 44, 2):
        rows_clean.append(rows[row_number])

    deaths_dict = dict()
    for row in rows_clean:
        row_split = row.split(">")
        if row_split[1][1].isdigit():
            region = row_split[1][5:-4]
        else:
            region = row_split[1][:-4]
        deaths_number = int(row_split[3][:-4])
        deaths_dict[region] = deaths_number
    return deaths_dict


def get_investigation_dict(parse_initial_investigation):
    initial_investigation = str(parse_initial_investigation)
    rows = initial_investigation.split("li>")
    split_date = rows[1].replace('\xa0', ' ').split()[3:6]
    prelevement_date = " ".join(split_date)[:-12]
    print(prelevement_date)
    investigation_dict = dict()
    investigation_dict["date"] = prelevement_date
    investigation_keys = ["Prélèvements effectués", "Analyses réalisées", "Cas négatifs", "Cas confirmés"]
    rows_utiles = [1, 3, 5, 7]
    for row in enumerate(rows_utiles):
        investigation_dict[investigation_keys[row[0]]] = int(rows[row[1]].replace('\xa0', '').split()[-1][:-2])
    return investigation_dict, prelevement_date


parse_initial_case, parse_initial_deaths, parse_initial_investigation, parse_initial_hospitalisation, parse_data_cumulatives = parse_page_initial(URL, ID_1, ID_2, ID_3, ID_4, ID_5)

initial_case = str(parse_initial_case)
rows = initial_case.split("</tr>")
head_row = rows[0].replace('\xa0', ' ')
data_rows = rows[1:-2]
head_items = head_row.split("th>")[2:-2]
count_head = head_row.count("th>")

list_of_dates = [0]*len(head_items)
for item in enumerate(head_items):
    list_of_dates[item[0]] = item[1].split('>')[1][:-2]
tuple_of_dates = tuple(list_of_dates)
#print(tuple_of_dates)

dict_number_cases = dict()
for row in data_rows:
    row = row.replace('\xa0', '')
    region_name = row.split("td>")[1]
    if region_name.startswith("0") or region_name.startswith("1"):
        region_name = region_name.split()[2:][0][:-2]
    else:
        region_name = region_name[:-2]
    row_initial = row.split("td>")[2:-2] #change variable name

    list_num = [0]*(len(row_initial))
    for td in enumerate(row_initial):
        list_num[td[0]] = extract_number(td[1])
    dict_number_cases[region_name] = list_num

today_number_case_dict = dict()
list_of_dicts = list()

#list_of_actual_dates = check_date("covid_qc")
for date in enumerate(list_of_dates):
    today_number_case_dict["date"] = date[1]
    for region in dict_number_cases:
                today_number_case_dict[region] = int(dict_number_cases[region][date[0]])
    update_data_file("covid_qc_octobre", today_number_case_dict)
    #list_of_dicts.append(today_number_case_dict)

investigation_dict, prelevement_date = get_investigation_dict(parse_initial_investigation)
update_data_file("covid_qc_investigation", investigation_dict)

hospitalisation_dict, date = get_hospitalisation_dict(parse_initial_hospitalisation)
# print(hospitalisation_dict)
update_data_file("covid_qc_hospitalisation", hospitalisation_dict)

deaths_dict = get_deaths_dict(parse_initial_deaths)
deaths_dict["date"] = date
#print(deaths_dict)
update_data_file("covid_qc_deaths", deaths_dict)
