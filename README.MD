# REPOSITORIO DEL PROYECTO: DESARROLLO DE UN SISTEMA DE TELEMANIPULACIÓN REMOTA CON TECNOLOGÍA VESTIBLE PARA LA OPERACIÓN DEL ROBOT UR3 EN LABORATORIOS DE ALTO RIESGO QUÍMICO Y BIOLÓGICO 

Para Ejecutar cualquier código deben instalarse los sisguientes requerimientos:
 1. movelladot-pc-sdk 2023.6.0: Kit de desarrollo de software que permite crear aplicaciones en Windows y Linux para trabajar directamente con los sensores Xsens DOT. Incluye librerías básicas y APIs. Este sdk es compatible con la versión 3.0.0 de Movella
       -Se acceden a datos de acelerómetros, giroscopios y cuaterniones en tiempo real. 

       -Soporta **Python**, C++, C#, Java como lenguajes

       -Comunicación Bluetooth 5.0 BLE (10m)
      
       -Escaneo y conexión/desconexión de dispositivos DOT
      
       -Lectura de información básica: nombre, dirección MAC, versión de hardware/firmware, estado de batería.
      
       -Ajuste de perfiles

 2. Python 3.9 (compatible con el sdk)

 3. Numpy 2.0.2 Cálculos numéricos

 4. Pandas Tratamiento de datos

 5. Matplotlib Gráficas

 6. Queue - Cola segura para datos en tiempo real
 
 7. defaultdict - Diccionario que crea listas automáticamente

 8. pynput.keyboard - Detectar teclas 
 
 9. time - delays y temporización

# user_settings.py
Script con mobres generales del Movella y personalización de usuario

# xdpchandler.py
Script con la clase handler para: Detectar sensores Movella DOT, conectar por Bluetooth o USB, Escucha eventos (callbacks) del SDK, Recibe datos IMU en tiempo real y se pueden guardar.
La función "onLiveDataAvailable" da el Time stamp, Orientación en cuaterniones evitando gimball block (a implementar con filtros complementarios/magwick/kalman), aceleración lineal (sin bias gravitatoria) y giroscopio 

# modos_data.py
Paylods detectados

XsPayloadMode_OrientationQuaternion, XsPayloadMode_RateQuantitieswMag. XsPayloadMode_CompleteQuaternion,XsPayloadMode_ExtendedQuaternion.XsPayloadMode_DeltaQuantities,XsPayloadMode_DeltaQuantitieswMag,XsPayloadMode_HighFidelitywMag

# recordData.py
Guardar datos para post analisis

# plot2.py
Graficos en series de tiempos de las tres variables

#plot3.py
Grafico en 3D para orientación
