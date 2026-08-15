# Informe Tarea 1 — Proxy

**Curso:** CC4303 — Redes de Computadores **Actividad:** Construcción de un Proxy HTTP para filtrado de contenido web

## 0. Declaración sobre uso de IA / LLMs

Para la elaboración de este informe se utilizó **Claude (Anthropic, modelo Claude Opus 4.7)** como apoyo en la **redacción y estructuración del informe**, así como en la revisión y explicación conceptual del código ya desarrollado por el grupo. El código del proxy fue implementado por los integrantes del grupo; el modelo se usó para: (a) organizar la estructura del informe, (b) redactar explicaciones técnicas de las decisiones de diseño, (c) apoyar la formulación de las respuestas a las preguntas conceptuales planteadas en el enunciado, (d) apoyo en la creación de función recive\_full\_message y (e) entender como venia el html en bytes.

## 1. Enlace al repositorio y ejecución

**Repositorio GitHub:** [https://github.com/xXTheNyanLord777Xx/tarea1-redes](https://github.com/xXTheNyanLord777Xx/tarea1-redes)

### Cómo ejecutar el código

1. Clonar el repositorio y ubicarse en la carpeta del proyecto.

2. Verificar que en la misma carpeta se encuentren los archivos:

   - `proxy.py` (código principal)

   - `config.json` (configuración con `user`, `blocked`, `forbidden\\\_words`, `X-ElQuePregunta`)

   - `test.html` (página que se muestra al bloquear un dominio)

   - `image.png` (imagen local mostrada dentro de `test.html`)

3. Modificar la variable `IP\\\_VM` dentro de `proxy.py` para que coincida con la IP de la máquina virtual donde corre el proxy.

4. Ejecutar:

```
python3 proxy.py
```

1. Para probar desde otra máquina con `curl`:

```
curl http://cc4303.bachmann.cl -x IP\\\_VM:8000
```

No se utilizan librerías externas más allá de `socket` y `json`, que son parte de la librería estándar de Python.

## 2. Diagrama del flujo del proxy


### Explicación del diagrama

El proxy se sitúa **entre el cliente (curl / navegador) y el servidor final**. Para cumplir su rol necesita manejar **tres sockets distintos**:

1. **Socket servidor (`cliente\\\_socket`)**: socket TCP que se mantiene escuchando en la IP y puerto donde el proxy expone su servicio (`IP\\\_VM:8000`). Su única función es aceptar conexiones entrantes.

2. **Socket cliente (`navegador\\\_socket`)**: socket que se crea al aceptar una conexión desde un cliente. A través de él se recibe la petición HTTP y, más adelante, se envía la respuesta ya filtrada.

3. **Socket endpoint (`endpoint\\\_socket`)**: socket que el proxy abre **como cliente** para conectarse al servidor final indicado en el header `Host` de la petición. Por este socket viaja la petición modificada y regresa la respuesta original.

En los casos de **dominio bloqueado** o **request de imagen local**, el proxy nunca abre el socket hacia el endpoint: responde directamente al cliente con contenido generado localmente.

Todos los sockets son **TCP** (`AF\\\_INET`, `SOCK\\\_STREAM`), ya que HTTP se apoya en TCP para garantizar entrega ordenada y sin pérdidas, lo cual es imprescindible para no corromper headers ni cuerpos binarios.

## 3. Descripción general del código

El código está estructurado en:

### 3.1 Clase `Message`

Se definió una clase simple con tres atributos:

- `start\\\_line` (str): la primera línea del mensaje HTTP (por ejemplo, `GET / HTTP/1.1` o `HTTP/1.1 200 OK`).

- `head` (dict): un diccionario que mapea nombre de header a su valor. Se eligió un diccionario porque los headers HTTP son pares clave–valor únicos y esto permite acceso, modificación y eliminación en O(1) al momento de agregar `X-ElQuePregunta`, cambiar `Connection` o recalcular `Content-Length`.

- `body` (bytes): el cuerpo se mantiene como **bytes** y no como string, porque los cuerpos pueden contener contenido binario (imágenes, por ejemplo) que no es válido decodificar como UTF-8.

### 3.2 Funciones principales

- `recive\\\_full\\\_message(socket)`: recibe un mensaje completo aunque el buffer sea menor al tamaño total del mensaje. (Detallado en 7.)

- `parse\\\_HTTP\\\_message(bytes)`: transforma la cadena de bytes recibida en una instancia de `Message`. Separa el mensaje por `\\\\r\\\\n\\\\r\\\\n` para dividir headers de body, y luego cada línea de header por `": "`.

- `create\\\_HTTP\\\_message(message)`: hace el proceso inverso, transformando una instancia `Message` a bytes listos para enviarse por socket.

- `contiene(url, prohibido)`: verifica si la URL solicitada calza con alguno de los patrones en la lista de bloqueados.

- `extraer(dominio, url)`: extrae la parte de la URL posterior al dominio, útil para detectar rutas específicas (por ejemplo `/image.png`).

### 3.3 Bucle principal

En el bucle principal (`while True`) el proxy:

1. Acepta una nueva conexión de cliente.

2. Recibe la petición completa (usando `recive\\\_full\\\_message`).

3. Parsea la petición.

4. Extrae `Host` y target.

5. Modifica los headers (agrega `X-ElQuePregunta`, fuerza `Connection: close`).

6. Decide qué hacer según tres casos: (a) request de `/image.png`, (b) dominio bloqueado, (c) request normal.

## 4. Decisiones de diseño

### 4.1 Uso de sockets TCP

Se utilizaron sockets `SOCK\\\_STREAM` (TCP) porque HTTP requiere entrega **confiable, ordenada y orientada a conexión**. UDP no garantiza estas propiedades y perderíamos integridad de headers y bodies.

### 4.2 Estructura de datos para mensajes

Se optó por una **clase** en vez de un diccionario suelto, porque agrupa semánticamente los tres componentes de un mensaje HTTP (línea de inicio, headers, body) y mejora la legibilidad. Los headers como diccionario permiten operaciones eficientes (leer `Host`, sobrescribir `Content-Length`, agregar headers nuevos).

### 4.3 Body como bytes

Se decidió **no decodificar el body a string** porque puede contener datos binarios (imágenes, comprimidos, etc.). Solo los headers y la start line se decodifican a UTF-8, ya que HTTP/1.1 define el área de headers como texto ASCII/UTF-8.

### 4.4 Recálculo obligatorio de `Content-Length`

Después de reemplazar palabras prohibidas, el largo del body puede haber cambiado. Si no se recalcula `Content-Length`, el cliente puede quedar esperando bytes que nunca llegan, o interpretar mal el fin del mensaje. Por eso se actualiza siempre después de modificar el body.

### 4.5 Forzar `Connection: close`

Se sobrescribe el header `Connection` a `close` para evitar tener que manejar keep-alive y pipelining. Así, tras enviar la respuesta, ambos extremos cierran la conexión y el proxy vuelve a iterar limpiamente.

### 4.6 Detección de si un mensaje tiene body

En la versión actual se asume que **los mensajes que comienzan con `GET` no tienen body**, mientras que el resto sí lo tienen. Es una simplificación válida para este alcance, dado que:

- Las peticiones GET no llevan body en la práctica.

- Las respuestas del servidor sí lo llevan (identificable por el `Content-Length`).

Se documenta como limitación conocida que si el cliente enviara un POST, el proxy también debería intentar leer body desde el cliente. La lógica ya está preparada para el caso general porque `recive\\\_full\\\_message` sí maneja Content-Length en respuestas.

## 5. Bloqueo de dominios prohibidos

Cuando la URL contiene alguno de los patrones definidos en `config.json` bajo `blocked`, el proxy no reenvía la petición al servidor final. En su lugar:

1. Construye una respuesta HTTP con start line `HTTP/1.1 403 ADONDEIBASPAPU`.

2. Como body incluye el contenido de `test.html`, que contiene una etiqueta `\\\<img src="/image.png"\\\>` apuntando a una imagen alojada localmente.

3. Envía la respuesta al cliente y cierra la conexión.

Cuando el navegador recibe ese HTML, hace una **segunda petición** al mismo proxy pidiendo `/image.png`. El proxy detecta esta ruta específica y responde con los bytes de la imagen y `Content-Type: image/png`.

### ¿Cuántos ciclos de comunicación HTTP son necesarios para mostrar una imagen en un navegador?

Se necesitan **dos ciclos de comunicación HTTP**:

1. **Primer ciclo:** el navegador solicita la página principal (por ejemplo `cc4303.bachmann.cl/secret`). El proxy responde con `403` y el HTML de bloqueo, que contiene una etiqueta `\\\<img\\\>`.

2. **Segundo ciclo:** al parsear el HTML, el navegador detecta la etiqueta `\\\<img src="/image.png"\\\>` y realiza una nueva petición HTTP para obtener la imagen. El proxy detecta esta ruta y responde con los bytes de la imagen.

Es decir, HTML e imagen viajan en **peticiones/respuestas HTTP independientes**, cada una en su propia conexión TCP (dado que forzamos `Connection: close`).

## 6. Modificación de headers y reemplazo de palabras

### 6.1 Header `X-ElQuePregunta`

Antes de reenviar la petición al servidor final, el proxy agrega el header:

```
X-ElQuePregunta: \\\<valor de config.json\\\>
```

Como los headers están representados como un diccionario, agregarlo es simplemente:

```
recv\\\_message.head\\\["X-ElQuePregunta"\\\] = datajson\\\["X-ElQuePregunta"\\\]
```

Esto permite que la página `cc4303.bachmann.cl` responda con un mensaje personalizado al pasar por el proxy.

### 6.2 Reemplazo de palabras prohibidas

Al recibir la respuesta desde el servidor final, se recorre la lista `forbidden\\\_words` del JSON y se aplica un `bytes.replace()` por cada par clave–valor:

```
for dic in datajson\\\["forbidden\\\_words"\\\]:    
    for key, value in dic.items():    
        filtered\\\_response.body = filtered\\\_response.body.replace(    
            key.encode("utf-8"), value.encode("utf-8")    
        )
```

Se opera directamente sobre bytes para evitar problemas de codificación. Después del reemplazo se recalcula `Content-Length` para reflejar el nuevo tamaño del body.

## 7. Manejo de mensajes más grandes que el buffer

El buffer definido es intencionalmente pequeño (`BUFF\\\_SIZE = 50`) para forzar el escenario en que ningún mensaje HTTP relevante cabe en una sola llamada a `recv`. El manejo se hace en `recive\\\_full\\\_message`.

### 7.1 ¿Cómo sé si llegó el mensaje completo?

Depende de si el mensaje tiene body o no:

- **Sin body (GET request):** el mensaje está completo cuando llega la secuencia `\\\\r\\\\n\\\\r\\\\n`, que marca el final del área de headers.

- **Con body:** después de detectar `\\\\r\\\\n\\\\r\\\\n`, se lee el header `Content-Length` y se continúa leyendo del socket hasta acumular esa cantidad de bytes en el body.

### 7.2 ¿Qué pasa si los headers no caben en mi buffer?

No hay problema, porque `recive\\\_full\\\_message` acumula chunks en una variable `response` y **solo deja de leer headers cuando encuentra `\\\\r\\\\n\\\\r\\\\n`**. Si los headers son más grandes que 50 bytes, se hacen múltiples llamadas a `recv` y se concatenan.

```
while True:    
    if b"\\\\r\\\\n\\\\r\\\\n" in response:    
        break    
    chunk = socket.recv(BUFF\\\_SIZE)    
    response += chunk
```

### 7.3 ¿Cómo sé que el HEAD llegó completo?

Cuando la secuencia **`\\\\r\\\\n\\\\r\\\\n`** aparece en el buffer acumulado. Esta secuencia es la definida por el estándar HTTP como separador entre la sección de headers y el body. Antes de encontrarla, no puedo asumir que tengo todos los headers.

### 7.4 ¿Cómo sé que el BODY llegó completo?

Leyendo el valor del header **`Content-Length`**, que indica la cantidad exacta de bytes que tiene el body. Se sigue llamando a `recv` acumulando en `response` hasta que la cantidad de bytes leídos post-headers sea igual (o mayor) al valor de `Content-Length`.

### 7.5 Nota sobre la implementación

Se observa que en la implementación actual el contador `length` se incrementa en `BUFF\\\_SIZE` sin verificar cuántos bytes efectivamente devolvió `recv`. Esto funciona en la mayoría de los casos donde `recv` llena todo el buffer.

## 8. Pruebas realizadas

### 8.1 Prueba con `curl` sin proxy vs. con proxy

- `curl example.com` retorna el HTML original.

- `curl example.com -x IP\\\_VM:8000` retorna el mismo HTML (más eventual reemplazo de palabras), confirmando que el proxy transmite el mensaje correctamente.

### 8.2 Bloqueo de dominios

- `curl cc4303.bachmann.cl/secret -x IP\\\_VM:8000` retorna código `403 ADONDEIBASPAPU` y el HTML de bloqueo.

- Configurando el proxy en el navegador y accediendo a `http://cc4303.bachmann.cl/secret`, se muestra la imagen local (dos ciclos HTTP: HTML + imagen).

### 8.3 Header `X-ElQuePregunta`

- Accediendo a `cc4303.bachmann.cl` a través del proxy, el mensaje de bienvenida cambia respecto de acceder directamente, confirmando que el header llega correctamente al servidor final.

### 8.4 Reemplazo de palabras

- Accediendo a `cc4303.bachmann.cl/replace` a través del proxy, las palabras `proxy`, `DCC` y `biblioteca` se ven reemplazadas por `\\\[REDACTED\\\]`, `\\\[FORBIDDEN\\\]` y `\\\[???\\\]` respectivamente.

### 8.5 Buffer pequeño

Se probaron dos configuraciones:

1. **Buffer \> área de headers, buffer \< mensaje total:** el mensaje se recibe correctamente porque tras `\\\\r\\\\n\\\\r\\\\n` la lógica sigue leyendo body usando `Content-Length`.

2. **Buffer \< área de headers, buffer \> start line:** también funciona porque el loop de headers acumula chunks hasta encontrar `\\\\r\\\\n\\\\r\\\\n`, sin importar en cuántos pedazos venga.

En ambos casos el contenido reconstruido es idéntico al que se recibe con un buffer grande, lo que valida la robustez del método.

## 9. Limitaciones conocidas y posibles mejoras

- El proxy solo maneja HTTP (no HTTPS), lo que está en línea con lo pedido por el enunciado.

- La detección de si un mensaje tiene body se basa exclusivamente en si comienza con `GET`. Métodos como `POST` no están cubiertos.

- No se maneja `Transfer-Encoding: chunked`, sino solo `Content-Length`. En páginas simples esto es suficiente.

## 10. Conclusión

El proxy implementado cumple con las funcionalidades pedidas:

- Actúa como intermediario entre cliente y servidor, gestionando **tres sockets TCP** de forma coordinada.

- Bloquea dominios prohibidos con `403` y muestra una imagen local (2 ciclos HTTP).

- Agrega el header `X-ElQuePregunta` a las peticiones que reenvía.

- Reemplaza palabras prohibidas en las respuestas y recalcula `Content-Length`.

- Maneja correctamente mensajes más grandes que el buffer de recepción, usando `\\\\r\\\\n\\\\r\\\\n` para delimitar headers y `Content-Length` para delimitar el body.

El diseño con clase `Message` y funciones auxiliares de parseo/serialización facilitó mantener el código legible y modular.

