# Sistema de Control de Riego Agricola

## Introduccion
Este software es una plataforma integral diseñada para la gestion administrativa y visual de sistemas de riego agricola. Permite el control detallado de padrones de campesinos, el registro de siembras, la gestion de cuotas y la visualizacion cartografica interactiva de parcelas. La aplicacion esta construida sobre una arquitectura modular en Python, utilizando SQLite como motor de base de datos y Tkinter para la interfaz grafica de usuario.

## Capacidades del Sistema

### 1. Gestion de Padron y Datos Maestros
El sistema permite la administracion centralizada de los datos de los campesinos, incluyendo informacion sobre la ubicacion de sus lotes (barrio, seccion/localidad), superficie en hectareas y estado de actividad. Los datos pueden ser cargados de forma masiva desde archivos CSV estructurados.

### 2. Control de Riegos y Siembras
Facilita el seguimiento de los ciclos agricolas, permitiendo registrar el tipo de cultivo en cada parcela, el numero de riegos aplicados y el estado actual de la siembra (activa/inactiva).

### 3. Administracion de Cuotas y Finanzas
Incluye un modulo completo para la gestion de cobros por diversos conceptos, tales como cuotas de mantenimiento, bombeo o servicios especiales. Permite la emision de recibos digitales, el registro de abonos y la generacion de estados de cuenta detallados por campesino o por concepto.

### 4. Cartografia Interactiva (GIS)
Provee una herramienta de visualizacion basada en datos geometricos vectoriales. Las parcelas se representan graficamente y pueden ser filtradas o coloreadas dinamicamente segun diversos criterios:
* Tipo de cultivo.
* Barrio de pertenencia.
* Seccion o localidad.
* Estado de la siembra.
* Intensidad de riegos (Mapa de calor).

### 5. Generacion de Reportes y Auditoria
El sistema genera documentacion profesional en formatos PDF y Excel:
* Recibos de pago individuales.
* Reportes diarios de ventas y recaudacion.
* Inventarios de siembras y distribucion de cultivos.
* Graficas estadisticas de distribucion espacial y economica.
* Historial retroactivo de reportes generados.

## Arquitectura del Proyecto

El software se divide en los siguientes modulos principales:

* **main.py**: Punto de entrada de la aplicacion que gestiona la inicializacion de bases de datos, migraciones y el arranque de la interfaz principal.
* **modules/ui_components.py**: Contiene la logica de las ventanas, formularios y componentes de la interfaz de usuario.
* **modules/mapa_interactivo.py**: Implementa el motor de visualizacion cartografica utilizando Matplotlib integrado en Tkinter.
* **modules/models.py**: Define el esquema de la base de datos, las relaciones entre tablas y las funciones de consulta SQL.
* **modules/reports.py**: Responsable de la logica de generacion de archivos PDF (ReportLab) y archivos Excel (Openpyxl).
* **modules/modern_sidebar.py**: Gestiona la navegacion lateral y la identidad visual de la aplicacion.
* **modules/utils.py**: Funciones utilitarias para manejo de rutas, hilos de ejecucion (threading) y procesamiento de archivos.

## Gestion de Datos

### Bases de Datos
El sistema utiliza dos bases de datos relacionales SQLite:
1. **riego.db**: Almacena el padron de campesinos, registros de siembras, recibos de riego y configuraciones generales del sistema.
2. **cuotas.db**: Almacena informacion especifica sobre tipos de cuotas, recibos de cobros y abonos financieros.

### Archivos de Datos Externos
* **XICUCO.csv**: Archivo de origen para la carga inicial de datos de usuarios y lotes.
* **database/mapa_geometria.json**: Almacena las coordenadas y metadatos de los poligonos que representan las parcelas en el mapa.

## Requisitos del Sistema e Instalacion

### Requisitos Tecnicos
* Python 3.10 o superior.
* Bibliotecas dependientes:
  * tkinter (Interfaz grafica).
  * matplotlib (Visualizacion de datos).
  * reportlab (Generacion de PDF).
  * openpyxl (Manejo de Excel).
  * sqlite3 (Motor de base de datos).
  * pillow (Procesamiento de imagenes).

### Instalacion
1. Clonar o copiar el repositorio en el directorio local.
2. Asegurar que las dependencias esten instaladas mediante el administrador de paquetes correspondiente.
3. Verificar la existencia de las carpetas `assets/`, `database/` y `modules/`.
4. Ejecutar el comando `python3 main.py` para iniciar la aplicacion.

## Procedimientos de Operacion

### Carga Inicial
Al iniciar por primera vez con bases de datos vacias, el sistema intentara cargar los registros desde el archivo `XICUCO.csv`. Es imperativo que dicho archivo mantenga la estructura de columnas esperada para evitar errores de parseo.

### Uso del Mapa
El mapa permite interaccion mediante el raton:
* **Zoom**: Utilizar la rueda del raton para acercar o alejar el plano.
* **Desplazamiento**: Clic izquierdo y arrastrar para navegar por el plano.
* **Seleccion**: Clic sobre una parcela para ver el detalle informativo en el panel lateral.

### Seguridad y Auditoria
El sistema implementa un registro de auditoria para operaciones criticas. Se recomienda realizar copias de seguridad periodicas de los archivos `.db` en el directorio `database/`.

## Notas de Desarrollo
Este software ha sido diseñado con un enfoque en la robustez y la facilidad de uso en entornos rurales o de asociaciones de riego. La modularidad del codigo permite futuras expansiones, como la integracion con sensores de flujo o sistemas de facturacion electronica.
