import requests
from bs4 import BeautifulSoup
import networkx as nx
from pyvis.network import Network
from urllib.parse import urljoin
import re

def get_soup(url):
    """Hilfsfunktion zum Abrufen und Parsen einer Webseite"""
    print(f"Rufe URL auf: {url}")
    response = requests.get(url)
    response.encoding = 'utf-8'  # Setze die Kodierung explizit auf UTF-8
    print(f"Status Code: {response.status_code}")
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup

def get_locations():
    """Extrahiert die Standorte und deren URLs von der Hauptseite"""
    base_url = 'https://www.fernuni-hagen.de/studium/regionalzentren/betreuung/index.shtml'
    print("\nSuche nach Standorten...")
    soup = get_soup(base_url)
    
    locations = {}
    
    # Suche nach allen ul.fu-link-list Elementen
    link_lists = soup.find_all('ul', class_='fu-link-list')
    print(f"Gefundene Link-Listen: {len(link_lists)}")
    
    for ul in link_lists:
        for li in ul.find_all('li'):
            link = li.find('a')
            if link:
                location_name = link.get_text(strip=True)
                # Überspringe spezielle Links
                if location_name in ['Termine für heute und morgen', 'Termine für weitere 7 Tage',
                                   'Alle Mentoriate - Campusstandort auswählen',
                                   'Teilnahmebescheinigung zum Download',
                                   'Veranstaltungen an den Campusstandorten']:
                    continue
                
                # Normalisiere die URL
                href = link.get('href', '')
                if href.startswith('/'):
                    location_url = urljoin('https://www.fernuni-hagen.de', href)
                else:
                    location_url = urljoin(base_url, href)
                
                print(f"Gefunden: {location_name} -> {location_url}")
                locations[location_name] = location_url
    
    print(f"\nGefundene Standorte: {len(locations)}")
    return locations

def get_modules_for_location(location_url):
    """Extrahiert die Modulinformationen von der Standortseite"""
    print(f"\nVerarbeite Standort-URL: {location_url}")
    soup = get_soup(location_url)
    modules = []
    
    # Suche nach der Tabelle mit den Modulinformationen
    tables = soup.find_all('table')
    print(f"Gefundene Tabellen: {len(tables)}")
    
    for i, table in enumerate(tables):
        print(f"\nAnalysiere Tabelle {i+1}:")
        rows = table.find_all('tr')
        print(f"Gefundene Zeilen: {len(rows)}")
        
        # Überprüfe die Spaltenüberschriften
        headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
        print(f"Gefundene Spalten: {headers}")
        
        if not any('modulnr' in header or 'modul' in header for header in headers):
            print("Überspringe Tabelle - keine Moduldaten")
            continue
            
        for row in rows[1:]:  # Überspringe die Kopfzeile
            cols = row.find_all('td')
            if len(cols) >= 3:
                # Versuche verschiedene Spaltenindizes für die Daten
                module_nr = ''
                module_title = ''
                author = ''
                
                for col in cols:
                    text = col.get_text(strip=True)
                    if text and not module_nr and text.replace('.','').isdigit():
                        module_nr = text
                    elif text and not module_title and len(text) > 5:
                        module_title = text
                    elif text and not author:
                        author = text
                
                if module_nr and module_title:
                    print(f"Gefundenes Modul: {module_nr} - {module_title}")
                    link = None
                    for col in cols:
                        link = col.find('a')
                        if link:
                            break
                    
                    module_url = urljoin(location_url, link['href']) if link else None
                    modules.append({
                        'module_nr': module_nr,
                        'module_title': module_title,
                        'author': author,
                        'url': module_url
                    })
    
    print(f"Insgesamt gefundene Module: {len(modules)}")
    return modules

def create_graph(locations_data):
    """Erstellt einen Graphen aus den gesammelten Daten"""
    G = nx.Graph()
    
    print("\nErstelle Graph:")
    print(f"Anzahl Standorte: {len(locations_data)}")
    
    # Füge Knoten und Kanten hinzu
    for location, modules in locations_data.items():
        print(f"\nStandort {location}:")
        print(f"Anzahl Module: {len(modules)}")
        G.add_node(location, node_type='location')
        for module in modules:
            module_id = f"{module['module_nr']}: {module['module_title']}"
            G.add_node(module_id, node_type='module')
            G.add_edge(location, module_id)
    
    print(f"\nGraph erstellt:")
    print(f"Anzahl Knoten: {G.number_of_nodes()}")
    print(f"Anzahl Kanten: {G.number_of_edges()}")
    return G

def visualize_graph(G):
    """Erstellt eine interaktive Visualisierung des Graphen"""
    # Erstelle ein neues Netzwerk
    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="black")
    net.force_atlas_2based()
    
    # Füge die Knoten hinzu
    for node, attr in G.nodes(data=True):
        if attr['node_type'] == 'location':
            # Standorte als größere blaue Knoten
            net.add_node(node, label=node, color='#ADD8E6', size=30, title=f"Standort: {node}")
        else:
            # Module als kleinere grüne Knoten
            module_info = node.split(': ', 1)
            if len(module_info) == 2:
                module_nr, module_title = module_info
                net.add_node(node, label=module_nr, color='#90EE90', size=20, 
                            title=f"Modul: {module_title}\nModul-Nr: {module_nr}")
            else:
                net.add_node(node, label=node, color='#90EE90', size=20)
    
    # Füge die Kanten hinzu
    for edge in G.edges():
        net.add_edge(edge[0], edge[1])
    
    # Konfiguriere die Physik-Einstellungen für bessere Lesbarkeit
    net.set_options('''
    {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -100,
          "centralGravity": 0.01,
          "springLength": 200,
          "springConstant": 0.08
        },
        "maxVelocity": 50,
        "minVelocity": 0.1,
        "solver": "forceAtlas2Based",
        "timestep": 0.35
      },
      "interaction": {
        "hover": true,
        "navigationButtons": true,
        "keyboard": {
          "enabled": true
        }
      }
    }
    ''')
    
    # Speichere den Graphen als HTML-Datei
    net.save_graph("mentoring_graph.html")
    print("Interaktiver Graph wurde als 'mentoring_graph.html' gespeichert.")

def main():
    # Sammle alle Daten
    print("Sammle Standorte...")
    locations = get_locations()
    
    # Sammle Module für jeden Standort
    locations_with_modules = {}
    for location_name, location_url in locations.items():
        print(f"Verarbeite Standort: {location_name}")
        modules = get_modules_for_location(location_url)
        locations_with_modules[location_name] = modules
    
    # Erstelle und visualisiere den Graphen
    print("Erstelle Graph...")
    G = create_graph(locations_with_modules)
    
    print("Visualisiere Graph...")
    visualize_graph(G)
    print("Fertig! Der Graph wurde als 'mentoring_graph.html' gespeichert.")

if __name__ == "__main__":
    main() 