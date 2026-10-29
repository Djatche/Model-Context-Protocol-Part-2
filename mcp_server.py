import os
import math
from fastmcp import FastMCP

# Create an MCP server instance
mcp = FastMCP("polio vaccine estimation")

@mcp.tool
def polio_vaccine_estimator(
    population: int,
    vaccine_coverage: int = 100, 
    proportion_u59: float = 0.2, 
    dose_vial: int = 20, 
    wastage_rate: float=0.15, 
    safety_stock: float=0.15
    ) -> str:
    """
    Estimate the nomber of vials of polio vaccine oral for a given population number.

    Args:
        population: the total population number.
        vaccine_coverage: Expected vaccination coverage (in percentage, e.g., 100).
        proportion_u59: Proportion of children under 59 months among total population. 
                          e.g., 0.15 if 15% of the population are under 59 months old.
        dose_vial: Number of doses per vial.
        wastage_rate: Proportion of vaccine vials wasted (e.g., 0.15 for 15%).
        safety_stock:Proportion of additional safety stock required (e.g., 0.15 for 15%).
    Returns:
        An integer representing the estimated total number of vials needed.
    """

    # 1. Calcul du nombre d'enfants cibles de moins de 59 mois
    target_children = population * proportion_u59 * (vaccine_coverage / 100.0)

    # 2. Nombre total de doses nécessaires en tenant compte du taux de perte (wastage rate)
    # Formule standard OMS : Doses nettes / (1 - taux de perte)
    doses_needed = target_children / (1.0 - wastage_rate)

    # 3. Ajout du stock de sécurité
    total_doses_with_stock = doses_needed * (1.0 + safety_stock)

    # 4. Conversion en nombre de flacons (arrondi supérieur)
    total_vials = math.ceil(total_doses_with_stock / dose_vial)

    return f'the number of polio oral vaccine vials :{total_vials}'



@mcp.prompt(title="opv estimaor")
def opv_estimator_prompt(estimation_request:str) -> str:
    return f"""You are the logistician for the Expanded Programme on Immunization at the regional level for the polio vaccination campaign.
    Your task is to:
    1. Extract the total population, the wastage rate, the number of dose of vaccine in a vial, the safety stock, Proportion of children under 59 months among total population and the vaccine coverage expected.
    2. Use the estimator tool to give the number of dials for oral polio vaccine needed

    Default values to use if not specified by the user:
    - Vaccine coverage: 100%
    - Wastage rate: 0.15
    - Safety stock: 0.15
    - Doses per vial: 20
    - Proportion under 59 months: 0.15

    Rules:
    - If population are ambiguous or missing, ask the user for clarification 

    User's estimation request: {estimation_request}"""


FILE_PATH = os.path.abspath("default_value.txt")

@mcp.resource("config://vaccine-default-params-value")
def get_default_params_value()->str:
    """Provides default vaccination and demographic parameters to enrich context."""
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        return f.read()



if __name__ == "__main__":
    mcp.run(transport="stdio")
    



    


