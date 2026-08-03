import data_type as data
from ingestion import ingest
from pathlib import Path

def menu():
    print("TUPAN DIGITAL SYSTEM")
    print("1. Registro Manual")
    print("2. Pesquisa")
    print("3. Registro Automático")
    print("4. Sair")
    
    choice= input("Digite sua escolha: ")
    if choice == "1":
        manual_register()
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
        """need to know how does the file looks like"""
        with open(path, "r") as f:
            print(f.read())
    else:
        print("Path does not exist")
        print("REGISTRANDO BANCO DE DADOS...")

def manual_register():
    print("REGISTRAR NOVO IMOVEL")
    price= float(input("Digite o valor do imóvel: "))
    area= float(input("Digite a área do imóvel em metros quadrados: "))
    age= int(input("Digite quando o imóvel foi construído: "))
    number_of_rooms= tuple(map(int, input(
        "Digite o número de quartos (suítes e quartos separados por -> S Q): ").split()))
    number_of_bathrooms= int(input("Digite o número de banheiros: "))
    number_of_parking_spaces= int(input("Digite o número de vagas: "))
    last_sale_price= float(input("Digite o valor da venda mais recente: "))
    last_sale_date= input("Digite a data da ultima venda (dd/mm/aaaa): ")
    square_meter_price= price / area if area > 0 else 0

    real_estate= data.RealEstate(
        name= input("Digite o nome do imóvel: "),
        address= input("Digite o endereço do imóvel: "),
        price= price,
        area= area,
        age= age,
        number_of_rooms= number_of_rooms,
        number_of_bathrooms= number_of_bathrooms,
        number_of_parking_spaces= number_of_parking_spaces,
        last_sale_price= last_sale_price,
        last_sale_date= last_sale_date,
        square_meter_price= square_meter_price  
    )

    index= ingest(real_estate)
    print("OPERAÇÃO CONCLUÍDA COM SUCESSO")
    return index