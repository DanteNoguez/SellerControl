
import pandas as pd
import numpy as np
import re

def merge_data(teika1: str, teika2: str, mercadolibre: str):
  """
  Esta función une los reportes de Amazon y Mercadolibre con base en el SKU.

  Args:
  Es necesario entrecomillar e ingresar el nombre de cada archivo con terminación .csv o .xlsx

  teika1: el nombre del reporte quincenal descargable en Teikametrics -> Product catalog.
  teika2: el nombre del reporte mensual descargable en Teikametrics -> Product catalog.
  mercadolibre: el nombre del reporte descargable en MercadoLibre -> Publicaciones -> Gestión de stock Full -> Descargar reportes de stock (reporte general de stock).

  Returns:
  El resultado es un archivo de Excel con el SKU, nombre de los productos, ventas, estimación de ventas e inventario de ambas plataformas.

  Ejemplo de uso:
    merge_data('teikametrics1.csv', 'teikametrics2.csv', 'mercadolibre.xlsx')

  """
  
  # Cargar datos quincenales 
  amz_quincena = pd.read_csv(teika1).iloc[:,[0, 1, 8, 11, -1]]
  amz_quincena = pd.DataFrame(amz_quincena).rename(columns={'Units Sold': 'Ventas AMZ última quincena', 'Previous Units Sold': 'Ventas AMZ penúltima quincena', 'Current inventory quantity': 'Stock AMZ', 'SKU Name': 'Producto'}).sort_values('Producto', ignore_index=True)

  # Cargar datos mensuales
  amz_mes = pd.read_csv(teika2).iloc[:,[0, 1, 8, 11, -1]]
  amz_mes = pd.DataFrame(amz_mes).rename(columns={'Units Sold': 'Ventas AMZ último mes', 'Previous Units Sold': 'Ventas AMZ penúltimo mes', 'Current inventory quantity': 'Stock AMZ', 'SKU Name': 'Producto'}).sort_values('Producto', ignore_index=True)

  # Cargar datos de Amazon
  meli = pd.read_excel(mercadolibre, skiprows=3).fillna(0).drop(index=0, columns='Título de la publicación').iloc[:, [1, 7, -1]]

  # Juntar reportes y acomodar columnas
  reinv = pd.merge(amz_quincena, amz_mes, how='outer').fillna(0)
  reinv = reinv[['SKU', 'Producto', 'Ventas AMZ penúltima quincena', 'Ventas AMZ última quincena', 'Ventas AMZ penúltimo mes', 'Ventas AMZ último mes', 'Stock AMZ']]
  reinv = pd.merge(reinv, meli, how='outer').fillna(0)
  reinv = reinv.rename(columns={'Ventas últimos 30 días (u.)': 'Ventas MELI último mes', 'Stock total almacenado': 'Stock MELI'})
  reinv[['Estimación AMZ', 'Estimación MELI']] = 0, 0
  reinv = reinv[['SKU', 'Producto', 'Ventas AMZ penúltima quincena', 'Ventas AMZ última quincena', 'Ventas AMZ penúltimo mes', 'Ventas AMZ último mes', 'Ventas MELI último mes', 'Estimación AMZ', 'Estimación MELI', 'Stock AMZ', 'Stock MELI']]
  
  # Calcular y cargar estimaciones de ventas con NumPy
  ventas = reinv[['Ventas AMZ penúltima quincena', 'Ventas AMZ última quincena', 'Ventas AMZ penúltimo mes', 'Ventas AMZ último mes', 'Ventas MELI último mes']].to_numpy()
  func_estimacion = lambda x: (np.amax([x[0]*2, x[1]*2, x[2], x[3]])*3) + (np.std([x[0]*2, x[1]*2, x[2], x[3]]))
  est_amz = np.fromiter(map(func_estimacion, ventas), dtype=int)
  estimacion_amazon = np.vstack((ventas.T, est_amz)).T
  vmeli = reinv['Ventas MELI último mes'].to_numpy()
  estimacion_meli = vmeli*3
  resultado = np.vstack((estimacion_amazon.T, estimacion_meli)).T
  reinv.iloc[:, 2:9] = resultado

  # Convertir a excel
  reinv.to_excel('reinv.xlsx')

  return reinv

from io import BytesIO
from pyxlsb import open_workbook as open_xlsb

def to_excel(df):
  """
  Función para hacer descargable el archivo en Streamlit
  """
  output = BytesIO()
  writer = pd.ExcelWriter(output, engine='xlsxwriter')
  df.to_excel(writer, index=False, sheet_name='Sheet1')
  workbook = writer.book
  worksheet = writer.sheets['Sheet1']
  format1 = workbook.add_format({'num_format': '0.00'}) 
  worksheet.set_column('A:A', None, format1)  
  writer.save()
  processed_data = output.getvalue()
  return processed_data
