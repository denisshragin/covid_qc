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
ID_1 = "c63027" #div today cases
ID_2 = "c63029" #div today deaths
ID_3 = "c50212" #div today under investigation
ID_4 = "c50210" #div nombre d’hospitalisations
ID_5 = "c63047" #div Données cumulatives, date
REGIONS = ["Bas-Saint-Laurent", "Saguenay – Lac-Saint-Jean", "Capitale-Nationale", "Mauricie-et-Centre-du-Québec", "Estrie", "Montréal", "Outaouais", "Abitibi-Témiscamingue", "Côte-Nord", "Nord-du-Québec", "Gaspésie – Îles-de-la-Madeleine", "Chaudière-Appalaches", "Laval", "Lanaudière", "Laurentides", "Montérégie", "Nunavik", "Terres-Cries-de-la-Baie-James", "Hors Québec", "Région à déterminer"]

def parse_page_initial(url, id_1, id_2, id_3, id_4, id_5):
    driver = webdriver.Chrome()
    driver.get(url)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()
    initial_case = soup.find("div", id = id_1).get_text()
    initial_deaths = soup.find("div", id = id_2).get_text()
    initial_investigation_number = soup.find("div", id = id_3).get_text()
    initial_hospitalisations = soup.find("div", id = id_4).get_text()
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

def excel_append(filename, today_data_dict):
    df_read = pd.read_excel(filename+".xlsx")
    df_new = df_read.append(today_data_dict, ignore_index = True)
    with pd.ExcelWriter(filename+".xlsx") as writer:
        df_new.to_excel(writer, index=False)

def update_data_file(filename, today_data_dict):
    filename_ext = filename+".txt"
    with open(filename_ext, "r", encoding = "utf-8") as f:
        if date not in f.read():
            with open(filename_ext, "a", encoding = "utf-8") as f:
                f.write(date + " ")
                f.write(str(today_data_dict))
                f.write("\n")
            excel_append(filename, today_data_dict)

parse_initial_case, parse_initial_deaths, parse_initial_investigation_number, parse_initial_hospitalisation, parse_data_cumulatives = parse_page_initial(URL, ID_1, ID_2, ID_3, ID_4, ID_5)

today_number_case = parse_initial_case.split(sep = ' - ')[1:]
print(parse_initial_case)
date = parse_data_cumulatives.split(sep =',')[2].strip().replace('\xa0', ' ')

today_number_case_list = append_terres_cries_data(today_number_case)
today_number_case_dict = today_data_dict(today_number_case_list, date, '\xa0', ' ')

update_data_file("covid_qc", today_number_case_dict)

today_number_deaths = parse_initial_deaths.split(sep=' - ')[1:]
today_number_deaths_list = append_terres_cries_data(today_number_deaths)
today_number_deaths_dict = today_data_dict(today_number_deaths_list, date, '\xa0', ' ')

update_data_file("covid_qc_deaths", today_number_deaths_dict)

inv_num_index_1 = parse_initial_investigation_number.find("confirmés")
inv_num_index_2 = parse_initial_investigation_number.find("Les plus récentes")
investigation_slice = parse_initial_investigation_number[inv_num_index_1:inv_num_index_2].replace("\xa0", " ")
# with open("investigation_slice.txt", "w", encoding="utf-8") as f:
#     f.write(investigation_number_slice)
# with open("investigation_slice.txt", "r", encoding="utf-8") as f:
#     investigation_slice = f.read()
# investigation_slice_2 = investigation_slice.replace("\xa0", " ")
pattern_date = r"Prélèvements effectués le ([0-9]+ [a-z]+) [0-9]* : ([0-9]+ [0-9]+)"
pattern_analyses = r"Analyses réalisées le ([0-9]+ [a-z]+) [0-9]* : ([0-9]+ [0-9]+)"
pattern_negatif = r"Cas négatifs[0-9]* : ([0-9]+ [0-9]+)"
pattern_confirmed = r"Cas confirmés[0-9]* : ([0-9]+ [0-9]+)[0-9]{1}"
result_date = re.search(pattern_date, investigation_slice)
result_analyses = re.search(pattern_analyses, investigation_slice)
result_negatif = re.search(pattern_negatif, investigation_slice)
result_confirmed = re.search(pattern_confirmed, investigation_slice)
print (investigation_slice)
print(result_date.groups()[0], result_date.groups()[1])
print(result_analyses.groups()[1])
print(result_negatif.groups()[0])
print(result_confirmed.groups()[0])

#investigation_number = investigation_number_slice[investigation_number_slice.find('Personne'):(len(investigation_number_slice)-3)]
today_investigation_number_dict = {}
#today_investigation_number_dict["Personne sous investigation"] = investigation_number[:investigation_number.find('Cas')].split(':')[1]
today_investigation_number_dict["Prélèvements effectués"] = result_date.groups()[1]
today_investigation_number_dict["Analyses réaliséés"] = result_analyses.groups()[1]
today_investigation_number_dict["Cas négatifs"] = result_negatif.groups()[0]
today_investigation_number_dict["Cas confirmés"] = result_confirmed.groups()[0]

remove_sub(today_investigation_number_dict, ' ')
dict_str_to_int(today_investigation_number_dict, date)
del today_investigation_number_dict['total']


today_hospitalisation_number = parse_initial_hospitalisation.split(sep = ':')[1:4] 
today_hospitalisation_number_dict = {}
today_hospitalisation_number_dict["Nombre d’hospitalisations régulières"] = today_hospitalisation_number[0].strip().split("Nombre")[0]
today_hospitalisation_number_dict["Nombre en soins intensifs"] = today_hospitalisation_number[1].strip().split("Nombre")[0]
today_hospitalisation_number_dict["Nombre total d'hospitalisations"] = today_hospitalisation_number[2].strip()[0:-1]
remove_sub(today_hospitalisation_number_dict, '\xa0')
remove_sub(today_hospitalisation_number_dict, ' ')
dict_str_to_int(today_hospitalisation_number_dict, date)
del today_hospitalisation_number_dict['total']


update_data_file("covid_qc_investigation", today_investigation_number_dict)
update_data_file("covid_qc_hospitalisation", today_hospitalisation_number_dict)

print(today_number_case_dict)