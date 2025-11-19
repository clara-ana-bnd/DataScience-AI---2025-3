import regex as re
import pandas as pd
import json
import csv
import os
import time
from google import genai
from google.genai import types

def generate(abstract):
    client = genai.Client(
        api_key="", ## INSERIR CHAVE API
    )

    model = "gemini-flash-latest"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="""You want to find the adsorption data for metalic ions on porous materials,
                such aerogels, cryogels and hydrogels. Extract the data from scientific articles, identify the target ion,
                the adsorbent material, its respective composition, the maximum adsorbtion capacity and the adsorption efeciency.
                Output the results should be in a tuple format, each tuple must to have the following infomations: ion, ion_formula, 
                material type, material composition, maximum adsorpition capacity and adsorption efficiency, every tuple must to have six
                elements, in this order, if you don't identify any propertie, return the values as "None".                                   
                Each adsorbent material informations should be in a separate tuple, 
                you should to find the values for each material in the extracted data. 

                Check some examples for an extraction:
                ("Chromium", "Cr(VI)", "aerogel", "MOFs and cellulose nanofibers", None, "67 %"),
                                     
                ("Cadmium", "None", "aerogel", "silica aerogel activated carbon", "0.384 mg/g", "60 %")
                
                ("Cadmium", "Cd(II)", "aerogel", "sulfonated reduced graphene oxide (3D-SRGO)", "234.8 mg/g", "93 %")
                                     
                ("Nickel", "Ni(II)", "cryogel", "activated charcoal", "135.8 mg/g", "98 %")
                
                Rules:
                - Ignore non-phisical property information.
                - The ions name must to begin in upcase.
                - If information is unclear or there are more materials than properties, output None.
                - Prefer precise extractions over quantity.
                - Follow these instruction precisely!
                """),
            ],
        ),
        types.Content(
            role="user",
            # Use an f-string by starting the triple quotes with 'f'
            parts=[
                types.Part.from_text(text=f"""
                Analyze the following abstract text and extract the properties according to the instructions above:

                **ABSTRACT TEXT START**
                {abstract}
                **ABSTRACT TEXT END**
                """),
            ],
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        max_output_tokens=8000,
        thinking_config = types.ThinkingConfig(
            thinking_budget=0,
        ),
        # Removed image_config as it's not relevant for text-only tasks
        response_mime_type="application/json",
        system_instruction=[
            types.Part.from_text(text="""You are a bot mining for properties of adsorbets materials for remove ions from water from literature's abstracts.
            You will receive detailed information on the format you will need to output the extracted information.
            Do not deviate from the instructions. Your output should only have the information on the requested format, nothing else."""),
        ],
    )

    # 1. Call the API to get the full response object.
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )

    # 2. Return ONLY the text content of the response, which will be your JSON string.
    return response.text

########################################################### PUXANDO OS ARTIGOS 

df = pd.read_excel("dataframe_artigos_reduzido.xlsx")

abstracts = list()
for abst in df['Abstract']:
    abstracts.append(str(abst))

num_abstracts = len(abstracts)

outputs = list()
i = 0

########################################################### EXECUTANDO A FUNÇÃO

# Pasta onde os arquivos JSON serão salvos
output_dir = r'output-6' 

for abstract in abstracts:
    print(f'Processing Abstract {i} of {num_abstracts}')
    # print(abstract)
    response = None
    attempt = 1

    if re.search(r'[Mm]g\s*/?\s*g(?:[-−⁻]1)?', abstract):
        while attempt <= 2:  # tenta no máximo duas vezes
            try:
                response = generate(abstract)
                outputs.append(response)
                print(response)
                # time.sleep(6.5)
                break

            except Exception as e:
                error_message = str(e)
                print(f'API Response Error (tentativa {attempt}): {error_message}')

                if "RESOURCE_EXHAUSTED" in error_message or "quota" in error_message.lower():
                    print("Quota excedida — aguardando 2 minutos antes de tentar novamente...")
                    time.sleep(120)
                    attempt += 1  # tenta novamente

                else:
                    outputs.append("Error")
                    break

        if response is None:
            print(f"Falha permanente no Abstract {i}, pulando...\n")
            outputs.append("Error")

    print()
    i += 1


with open('output_final', 'w', newline='', encoding='utf-8') as arquivo_csv:
    escritor_csv = csv.writer(arquivo_csv)
    
    for linha in outputs:
        escritor_csv.writerow(linha)

os.makedirs(output_dir, exist_ok=True)

for i, output in enumerate(outputs, start=1):
    if output != 'None':
        try:
            json_out = json.loads(output)

            if json_out:
                filename = f"resultado_{i}.json"
                filepath = os.path.join(output_dir, filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(json_out, f, ensure_ascii=False, indent=4)

                print(f"Arquivo salvo: {filename}")
            else:
                print(f"Resultado {i}: JSON vazio, não salvo.")
        except json.JSONDecodeError:
            print(f"Skipping invalid JSON output ({i}): {output}")
    else:
        pass
    print()


