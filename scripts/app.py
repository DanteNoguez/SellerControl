import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO
from pyxlsb import open_workbook as open_xlsb
import openpyxl
from openpyxl import Workbook

#@st.cache
def merge_data(teika1: str, teika2: str, mercadolibre: str):
  # Cargar datos quincenales 
  amz_quincena = pd.read_csv(teika1).iloc[:,[0, 2, 13, 14, -1]]
  amz_quincena = pd.DataFrame(amz_quincena).rename(columns={'Units Sold': 'Ventas AMZ última quincena', 'Previous Units Sold': 'Ventas AMZ penúltima quincena', 'Current inventory quantity': 'Stock AMZ', 'SKU Name': 'Producto'}).sort_values('Producto', ignore_index=True)

  # Cargar datos mensuales
  amz_mes = pd.read_csv(teika2).iloc[:,[0, 2, 13, 14, -1]]
  amz_mes = pd.DataFrame(amz_mes).rename(columns={'Units Sold': 'Ventas AMZ último mes', 'Previous Units Sold': 'Ventas AMZ penúltimo mes', 'Current inventory quantity': 'Stock AMZ', 'SKU Name': 'Producto'}).sort_values('Producto', ignore_index=True)

  # Cargar datos de MercadoLibre
  meli = pd.read_excel(mercadolibre, skiprows=3).fillna(0).drop(index=0, columns='Título de la publicación').iloc[:, [1, 7, -1]]

  # Juntar reportes y acomodar columnas
  reinv = pd.merge(amz_quincena, amz_mes, how='outer').fillna(0)
  reinv = reinv[['SKU', 'Producto', 'Ventas AMZ penúltima quincena', 'Ventas AMZ última quincena', 'Ventas AMZ penúltimo mes', 'Ventas AMZ último mes', 'Stock AMZ']]
  reinv = pd.merge(reinv, meli, how='outer').fillna(0)
  reinv = reinv.rename(columns={'Ventas últimos 30 días (u.)': 'Ventas MELI último mes', 'Stock total almacenado': 'Stock MELI'})
  reinv[['Estimación AMZ', 'Estimación MELI', 'Estimación total']] = 0, 0, 0
  reinv = reinv[['SKU', 'Producto', 'Ventas AMZ penúltima quincena', 'Ventas AMZ última quincena', 'Ventas AMZ penúltimo mes', 'Ventas AMZ último mes', 'Ventas MELI último mes', 'Estimación AMZ', 'Estimación MELI', 'Estimación total', 'Stock AMZ', 'Stock MELI']]
  
  # Calcular y cargar estimaciones de ventas con NumPy
  ventas = reinv[['Ventas AMZ penúltima quincena', 'Ventas AMZ última quincena', 'Ventas AMZ penúltimo mes', 'Ventas AMZ último mes', 'Ventas MELI último mes']].to_numpy()
  func_estimacion = lambda x: (np.amax([x[0]*2, x[1]*2, x[2], x[3]])*3) + (np.std([x[0]*2, x[1]*2, x[2], x[3]]))
  est_amz = np.fromiter(map(func_estimacion, ventas), dtype=int)
  estimacion_amazon = np.vstack((ventas.T, est_amz)).T
  vmeli = reinv['Ventas MELI último mes'].to_numpy()
  estimacion_meli = vmeli*3
  resultado = np.vstack((estimacion_amazon.T, estimacion_meli)).T
  estimacion_total = est_amz + estimacion_meli
  resultado = np.vstack((resultado.T, estimacion_total)).T
  reinv.iloc[:, 2:10] = resultado

  # Convertir a excel
  reinv.to_excel('reinv.xlsx')

  return reinv

def to_excel(df):
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

#logo = st.container()

#imagen = logo.image('/Users/dantenoguez/repos/stock_amz_meli/img/LOGODEZV.png', width=300)

st.markdown("# SellerControl ")
#st.subheader("by Dezvolta ")
#st.sidebar.markdown("# DEZVOLTA ")

features = st.container()
files = st.container()

with features:
  st.text('Los reportes utilizados para generar el archivo fusión son:') 
  code1 = "Reporte quincenal de Teikametrics: Teikametrics -> Product catalog -> Seleccionar fechas y habilitar periodos previos -> Export"
  code2 = "Reporte mensual de Teikametrics: Teikametrics -> Product catalog -> Seleccionar fechas y habilitar periodos previos -> Export"
  code3 = "MercadoLibre: MercadoLibre -> Publicaciones -> Gestión de stock Full -> Descargar reportes de stock -> Reporte general de stock"
  st.code(code1)
  st.code(code2)
  st.code(code3)

with files:
  st.subheader('Carga tus archivos aquí:')
  in_file, out_file = st.columns(2)

  teika1 = in_file.file_uploader('Carga el reporte de Teikametrics quincenal: ', type=['csv'])
  teika2 = in_file.file_uploader('Carga el reporte de Teikametrics mensual: ', type=['csv'])
  mercadolibre = in_file.file_uploader('Carga el reporte de MercadoLibre: ', type=['xlsx'])

  if teika1 and teika2 and mercadolibre:
    mensaje = out_file.subheader('Tu archivo está listo')
    resultados = to_excel(merge_data(teika1, teika2, mercadolibre))
    descarga = out_file.download_button('Descarga tu reporte.', data=resultados, file_name='stock.xlsx')