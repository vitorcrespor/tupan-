import data_type as data
from ingestion import ingest
from pathlib import Path

def menu():
    print("TUPAN DIGITAL SYSTEM\n")
    print("1. Registro Manual\n")
    print("2. Pesquisa\n")
    print("3. Registro Automático\n")
    print("4. Sair\n")
    
    choice= input("Digite sua escolha: ")
    if choice == "1":
        print("1. Imóvel\n")
        print("2. Cidade\n")
        print("3. Área\n")
        choice_1= input("Digite sua escolha: ")
        if choice_1 == "1":
            real_estate= data.real_estate()
            manual_register(real_estate)
        elif choice_1 == "2":
            city= data.city()
            manual_register(city)
        elif choice_1 == "3":
            area= data.area()
            manual_register(area)
            
    elif choice == "2":
        search()
    elif choice == "3":
        automatic_register()
    elif choice == "4":
        exit()
    else:
        print("Invalid choice")
        menu()
        
def search():
    """"""

def automatic_register():
    path= str(input("Digite o caminho do seu banco de dados: "))
    if path.exists():
        open(path, "r")
        
        with open(path, "r") as f:
            print(f.read())
    else:
        print("Path does not exist")
        print("REGISTRANDO BANCO DE DADOS...")

def manual_register(obj):
    for attr, attr_type in obj.__annotations__.items():
        user_input= input(f"Digite o valor do atributo {attr}: ")
    setattr(obj, attr, attr_type(user_input))
    
