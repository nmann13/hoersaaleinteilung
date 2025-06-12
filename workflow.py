from IPython.display import display, Markdown, FileLink
import ipywidgets as widgets
import math
import pandas as pd
import json
import io
import time



# -------------------
#  Benötigten Daten einlesen 
#--------------------

with open("data/subjects_mod.json", "r", encoding="utf-8") as file:
    subjects_dict = json.load(file)

with open("data/halls_extended.json", "r", encoding="utf-8") as file:
    halls_dict = json.load(file)


# -------------------
# Widgets erstellen
#--------------------

# Datum

date =  widgets.DatePicker(
    description='Datum:',
    style={'description_width': 'initial'}
)
# Print-Befehle anzeigen

output = widgets.Output()

#  Studis-Daten hochladen

student_uploader = widgets.FileUpload(accept='.csv', multiple=True, description = "csv-Liste der Studies")
df_files = []
subject= None
wrong_files = {}

def handle_upload(change):
    global df_files,students, subject, subject_pnr, wrong_files, demand
    if not date.value:
        with output:
            #output.clear_output() 
            print("Bitte ein Datum wählen.")
            return None
         
    uploaded = student_uploader.value
    output.clear_output() 
    for fileinfo in uploaded:
        content = fileinfo['content']
        filename = fileinfo['name']
        df = pd.read_csv(io.BytesIO(content), encoding='ISO-8859-1', sep = ";")
        pnr = str(df["pnr"].iloc[0])
        if len(df.columns) > 1:
            subject_act = subjects_dict[pnr][1]
            if subject is None:
                subject = subject_act
                subject_pnr = pnr
                df_files.append(df)
                with output:
                    print("Hörsaaleinteilung zur Prüfung",subject,"am",date.value.strftime("%d.%m.%Y"))
                    print(f"Die Datei {filename} enthält {len(df)} Studierende")
                
            elif subject_act != subject:
                wrong_files[filename]=(subject,pnr)
            else:
                df_files.append(df)
                with output:
                    print(f"Die Datei {filename} enthält {len(df)} Studierende")
                  
   
    if df_files:
        with output:
            print("Anzahl eingelesener Dateien:",len(df_files))
    else:
        print("⚠️ Keine Datei erfolgreich eingelesen.")

    if wrong_files:
        with output:
            #print("Anzahl nicht ⚠️ eingelesener Dateien:",len(wrong_files))
            print("⚠️ Nicht eingelesen:",list(wrong_files.keys()), "Grund: Fach passt nicht zur gesetzten Prüfung")
              
    demand = sum(len(df) for df in df_files)
    with output:
        print("Kapazität für",demand,"Studierende benötigt")
       
    
    
    students = remap_and_concat(df_files)
        
student_uploader.observe(handle_upload, names='value')

def remap_and_concat(df_files):
    
    columnname_variants = {
    "Matrikelnummer": ["Matrikelnummer","matrikelnummer","mtknr"],
    "Nachname":["Nachname","nachname"],
    "Vorname": ["Vorname","vorname"],
    "Versuch":["versuch","pversuch","Versuch"]
    }
    
    
    for df in df_files:
        rename_map = {}
        for target, variants in columnname_variants.items():
            for name in variants:
                if name in df.columns:
                    rename_map[name] = target
                    break   
            df.rename(columns=rename_map, inplace=True)
    
    students = pd.concat(df_files, ignore_index=True, join = 'outer') 
    students = students.sort_values(by = ["Matrikelnummer"])
    return students


# Hörsaalabfrage
    
halls_widgets = []

def update_gesamt_kapazitaet():
    selected_lecture_halls_temp  = {
        halls_widgets[i][0].name: halls_widgets[i][1].value
        for i in range(len(halls_widgets)) if halls_widgets[i][0].value
    }
    with output:
        print("Studierende:",len(students)," Aktuelle Kapazität:", sum(selected_lecture_halls_temp.values()))
        
def update_value(change):
    index = change.owner.index
    if change.new:
        halls_widgets[index][1].value = halls_dict[list(halls_dict.keys())[index]]
        halls_widgets[index][1].layout.visibility = 'visible'
       
    else:
        halls_widgets[index][1].layout.visibility = 'hidden'
        halls_widgets[index][1].value = 0

    output.clear_output()
    update_gesamt_kapazitaet()


def make_capacity_observer(initial_value, int_field, name):
    def check_change(change):
        new_val = change['new']
        if new_val > initial_value:
            int_field.layout.border = '2px solid red'

            with output:
                output.clear_output()
                print("Kapazität für ",demand,"Studierende benötigt")
                print(f"⚠️ Die Kapazität im Hörsaal '{name}' wurde überschritten.")
                print(f"Standardkapazität: {initial_value}, Eingabe: {new_val}")
                
                question = widgets.Label("Möchten Sie die Kapazität überschreiten?")
                buttons = widgets.ToggleButtons(options=['Ja', 'Nein'])

                def handle_decision(decision_change):
                    if decision_change['new'] == 'Nein':
                        int_field.value = initial_value
                        int_field.layout.border = '1px solid lightgray'
                        output.clear_output()
                        update_gesamt_kapazitaet()
                    elif decision_change['new'] == 'Ja':
                        #output.clear_output()
                        print(f"Kapazität von '{name}' wurde überschritten und akzeptiert.")
                    
                buttons.observe(handle_decision, names='value')
                display(widgets.VBox([question, buttons]))
                update_gesamt_kapazitaet()
                
        else:
            int_field.layout.border = '1px solid lightgray'
            with output:
                output.clear_output()
                update_gesamt_kapazitaet()
                
        #update_gesamt_kapazitaet()
    return check_change

for i, (name, max_kapazitaet) in enumerate(halls_dict.items()):
    check_box =  widgets.Checkbox(value=False, description=name)
    check_box.index = i
    check_box.name = name
    check_box.observe(update_value, "value")
    kapazitaet_field = widgets.IntText(value=max_kapazitaet, placeholder="Max Kapazität", layout=widgets.Layout(visibility='hidden', width="100px"))

     # Beobachter hinzufügen
    kapazitaet_field.observe(make_capacity_observer(max_kapazitaet, kapazitaet_field, name), names='value')
    
    halls_widgets.append(( check_box, kapazitaet_field))


n_halls = len(halls_widgets)
column1_end = math.ceil(n_halls / 3)
column2_end = 2 * math.ceil(n_halls / 3)

columns = [
    widgets.VBox([widgets.HBox(w) for w in halls_widgets[:column1_end]]),
    widgets.VBox([widgets.HBox(w) for w in halls_widgets[column1_end:column2_end]]),
    widgets.VBox([widgets.HBox(w) for w in halls_widgets[column2_end:]])
]


grid = widgets.HBox(columns)
  

# -------------------
#  Workflow starten
#--------------------

def start_workflow(b):
    global wf 

    if not date.value:
        with output:
            #output.clear_output() 
            print("Bitte ein Datum wählen.")
            
    if not student_uploader.value:
        with output:
           # output.clear_output() 
            print("Bitte eine csv-Datei mit Studierenden hochladen.")
        #return None
    # Hörsaalliste verarbeiten
    selected_lecture_halls  = {
        halls_widgets[i][0].name: halls_widgets[i][1].value
        for i in range(len(halls_widgets)) if halls_widgets[i][0].value
    }
    if len(selected_lecture_halls) == 0:
        with output:
            #output.clear_output() 
            print("Bitte mindestens einen Hörsaal wählen.")
        #return None
    #Reicht Kapazität der gewählten Hörsäle?
    with output: 
        print("Studierende:",len(students)," Aktuelle Kapazität:", sum(selected_lecture_halls.values()))
    if len(students) > sum(selected_lecture_halls.values()):
        with output:
            print(f"⚠️ Kapazität der gewählten Hörsäle nicht ausreichend")
            print("Studierende:",len(students)," Aktuelle Kapazität:", sum(selected_lecture_halls.values()))
            print("Bitte einen weiteren oder größeren Hörsaal wählen.")
        #return None
    

    subject_abb, subject_long, examiner, number, = subjects_dict[subject_pnr][:4]
    hilfsmittel_liste = subjects_dict[subject_pnr][4] 
    helper = "\\\\".join(f"- {item}" for item in hilfsmittel_liste)
    
    wf = WorkFlow(date.value, subject_abb, subject_long, examiner, number, helper, students, selected_lecture_halls)
    return None


class WorkFlow:
    def __init__(self, date, subject_abb, subject, examiner, number, helper, df_students, halls):
        self.year = date.year
        self.month = date.month
        self.day = date.day
        self.date = str(date.day) + "." + str(self.month) + "." + str(self.year)
        self.subject_abb = subject_abb
        self.subject = subject
        self.examiner = examiner
        self.number = number
        self.helper = helper
        self.df_students = df_students
        #self.remap_columns()
        self.halls = halls 
        self.filename = "Hörsaalbelegung_"  + str(self.subject_abb) + "_" + str(self.year) + "_" + str(self.month) + ".tex"
        self.sort_halls()
        self.make_tex_file()    


    
    def sort_halls(self):
        """
        Teilt den Studies einen Hörsaal zu und sortiert innerhalb der Hörsäle die Studies nach Nachnamen
        """
        hall_col = [hall for hall, number in self.halls.items() for _ in range(number) ]
        self.df_students["halls"] = hall_col[:len(self.df_students.index)]
        self.df_students = self.df_students.sort_values(by = ["halls", "Nachname"])
        #with output:
         #   print(self.df_students[["Nachname", "Vorname", "Matrikelnummer","Versuch","halls"]])

    
    def add_hall_tex(self, tex_text, hall, df):
        
        tex_text +=f"""\\noindent
        \\Large 
       \\Large 
        \\parbox{{5cm}}{{\\textbf{{Prüfung:}}}} {self.subject} \\\\
        \\parbox{{5cm}}{{\\textbf{{Prüfungsnummer:}}}} {self.number}\\\\
        \\parbox{{5cm}}{{\\textbf{{Hörsaal:}}}} {hall} \\\\
        \\parbox{{5cm}}{{\\textbf{{Datum:}}}} {self.date} \\\\
        \\parbox{{5cm}}{{\\textbf{{Prüfer:}}}} {self.examiner} \\\\

        \\noindent
        \\large
        \\parbox[t]{{5cm}}{{\\textbf{{Erlaubte Hilfsmittel:}}}} \\parbox[t]{{\\dimexpr\\textwidth-5cm}}{{\\raggedright {self.helper}}}\\\\
        
        \\vspace{{1cm}}
        \\noindent
        \\parbox{{5cm}}{{\\textbf{{Teilnehmer:}}}}        \\rule{{.4\\textwidth}}{{0.4pt}}
        """
        tex_text +=r"""
        {\small
        \begin{center}
        \begin{longtable}{|l|p{3cm}|p{3cm}|l|l|l|p{4cm}|}
        \hline
        Nr & Nachname & Vorname & Matrikel-Nr. & Versuch & anwesend & Bemerkung \\
        \hline\hline
        \endfirsthead
        
        \hline
        Nr & Nachname & Vorname & Matrikel-Nr. & Versuch & anwesend & Bemerkung \\
        \hline\hline
        \endhead
        
        \hline
        \multicolumn{7}{r}{\emph{Fortsetzung auf der nächsten Seite}} \\
        \endfoot
        
        \hline
        \endlastfoot
        """
        
        for i, (_, row) in enumerate(df.iterrows()):
            Matrikelnummer = row["Matrikelnummer"]
            Vorname = row["Vorname"]
            Nachname = row["Nachname"]
            Versuch = row["Versuch"]
        
            tex_text += f"{i+1} & {Nachname} & {Vorname} & {Matrikelnummer} & {Versuch} & & \\\\ \\hline\n"

        tex_text += r"""\end{longtable}
        \end{center}
        }
        \clearpage
        
        """
       
        return tex_text


    def make_tex_file(self):
        tex_text = """\\documentclass{article}
                    \\usepackage[a4paper, margin=2cm]{geometry}
                    \\usepackage{booktabs}
                    \\usepackage{longtable}
                    \\begin{document}
                    """
        df = self.df_students
        for hall  in set(df["halls"]):
            tex_text = self.add_hall_tex(tex_text, hall,  df[df['halls']==hall]) 

        # Einteilung

        for _  in set(df["halls"]):
            tex_text += rf"""
                    \begin{{table}}[h]
                    \begin{{center}}
                    \vspace{{1cm}}
                    \Huge
                    \textbf{{Prüfung: }} {self.subject}\\
                    \vspace{{1cm}}
                    \begin{{tabular}}{{|l|l|l|}}
                    \hline
                    Von & Bis & Raum \\ \hline\hline
                """
            for hall in set(df["halls"]):
                 tex_text += f"""{min(df[df["halls"]==hall]["Matrikelnummer"])}
                     &{max(df[df["halls"]==hall]["Matrikelnummer"])}
                     &{hall}\\\\\\hline"""
            tex_text += """ \\end{tabular}
                    \\end{center}
                    \\end{table}
                    
                     
            """
        tex_text += """\\end{document}"""
        
        with open(f"output/{self.filename}", "w", encoding="utf-8") as file:
            file.write(tex_text)
        with output:
            output.clear_output() 
            print(f"Es wurde eine Tex-File {self.filename} erstellt.")   
            time.sleep(3)
            print("Neustart mit den zwei kleinen Dreiecken in der Menüleiste.")
        return None

# -------------------
# Hörsaaleinteilung vornehmen
#--------------------


start_button = widgets.Button(description="Einteilung starten")
start_button.on_click(start_workflow)



print('Okay')