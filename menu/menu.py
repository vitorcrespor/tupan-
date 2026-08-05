from ingestion import ingest, get_index
import data_type as data
from pathlib import Path
import pandas as pd  # type: ignore[reportMissingImports]
import config
import agent
import prompts
from llama_index.core import Settings
# pyright: reportMissingImports=false


index= get_index()

def menu():
    print("TUPAN DIGITAL SYSTEM\n")
    print("1. Registro Manual\n")
    print("2. Pesquisa\n")
    print("3. Registro Automático\n")
    print("4. Conversar com Ulisses\n")
    print("5. Sair\n")
    
    choice= input("Digite sua escolha: ")
    if choice == "1":
        print("1. Imóvel\n")
        print("2. Cidade\n")
        print("3. Área\n")
        choice_1= input("Digite sua escolha: ")
        if choice_1 == "1":
            manual_register(data.real_estate)
        elif choice_1 == "2":
            city= data.city()
            manual_register(data.city)
        elif choice_1 == "3":
            area= data.area()
            manual_register(data.area)
            
    elif choice == "2":
        search()
    elif choice == "3":
        automatic_register()
    elif choice == "4":
        agent.ulisses()
    elif choice == "5":
        exit()
    else:
        print("Invalid choice\n")
        menu()

def automatic_register(cls):
    path= Path(input("Digite o caminho do seu banco de dados: "))
    if path.exists():
        df= pd.read_excel(path)
        print("REGISTRANDO BANCO DE DADOS...\n")
        for index,row in df.iterrows():
            obj= cls()
            for attr, attr_type in cls.__annotations__.items():
                attr_value= row[attr]
                setattr(obj, attr, attr_type(attr_value))
            normalize_address(obj)
            ingest(obj)
        index.storage_context.persist()
        print("OPERAÇÃO CONCLUÍDA COM SUCESSO\n")
    else:
        print("Path does not exist\n")
        

def manual_register(cls):
    obj= cls()
    for attr, attr_type in cls.__annotations__.items():
        user_input= input(f"Digite o valor do atributo {attr}: ")
        setattr(obj, attr, attr_type(user_input))
    normalize_address(obj)
    ingest(obj)
    index.storage_context.persist()
    
def search():
    choice_2= input("FILTRAR PESQUISAS?\n1. Sim\n2. Não\n")
    if choice_2 == "1":
        print("FILTROS DE PESQUISA:\n")
        attrs= list(data.real_estate.__annotations__.keys())
        for i, attr in enumerate(attrs):
            print(f"{i}. {attr}")
            
        filters: dict[str, tuple[float, float]] = {}
        values= [x.strip()
                for x in input("Filtros separados por vírgulas: ").split(",")]
        for value in values:
            minv= float(input(f"Digite o valor mínimo do filtro {attrs[int(value)]}: "))
            maxv= float(input(f"Digite o valor máximo do filtro {attrs[int(value)]}: "))
            filters[attrs[int(value)]] = (minv, maxv)
        where= prompts.build_where(filters)
    
    else: where= None
    
    search_query= input("Digite sua pesquisa: ")
    results= config.collection.query(
        query_texts=[search_query],
        n_results=5,
        where=where)     
    print("RESULTADOS DA PESQUISA:\n")
    
    for metadata in results["metadatas"][0]:
        print(metadata)
    #adicionar filtros de pesquisa, como cidade, área, faixa de preço, etc.
    
    
    
def normalize_address(obj):
    query= prompts.normalize_address(obj.address)
    response= Settings.llm.complete(query)
    obj.address= response.text
