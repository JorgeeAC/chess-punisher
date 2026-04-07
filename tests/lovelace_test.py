import requests
from bs4 import BeautifulSoup

def decode_secret_message(url: str) -> None:
    # going with Beautiful Soup for parsing
    soup = BeautifulSoup(requests.get(url, timeout=30).text, "html.parser")
    points = {}

    rows = soup.find_all("tr")
    #parsing table rows, grabbing columns as we go 
    for row in rows[1:]:  # Skip header row
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        # Based on link, column structure is x-coordinate [0], character [1], y-coordinate [2]
        # map to points dict with (x, y) as key and char as value
        char = cols[1].get_text().strip()
        x    = int(cols[0].get_text().strip())  # column, need to convert to int for grid indexing
        y    = int(cols[2].get_text().strip())  # row  , need to convert to int for grid indexing
        points[(x, y)] = char


    #grid size calculation
    max_x = max(x for x, _ in points)
    max_y = max(y for _, y in points)
    grid = [[" "] * (max_x + 1) for _ in range(max_y + 1)]

    
    for (x, y), char in points.items():
       grid[y][x] = char

    for row in grid:
        print("".join(row))


# --- Entry point ---
url = "https://docs.google.com/document/d/e/2PACX-1vSvM5gDlNvt7npYHhp_XfsJvuntUhq184By5xO_pA4b_gCWeXb6dM6ZxwN8rE6S4ghUsCj2VKR21oEP/pub"
decode_secret_message(url)