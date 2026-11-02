# Comprobaciones de robustez: qué resultados aguantan

## Qué se hizo
- El modelo de regresión se repitió cambiando una decisión cada vez, para ver si los resultados dependen de ella:
  - cómo se mide el compromiso (sus tres componentes por separado, o solo absentismo e impuntualidad);
  - los recursos de estudio por tramos en lugar de la escala de 0 a 6;
  - otros controles del centro (su nivel socioeconómico medio, la escasez de recursos según el director);
  - quitar cada uno de los 12 países, de uno en uno;
  - un panel ampliado de 25 países (sin la edición 2018), también quitando cada país.
- La aplicación usa siempre el modelo de partida (12 países). Estas comprobaciones solo sirven para decir cuánto
  fiarse de cada resultado.
- Los coeficientes están en puntos de matemáticas por desviación típica de la variable. «Cambio» es el coeficiente
  de 2022 menos el de 2012.

## Resultados que aguantan todas las comprobaciones
- **El compromiso se asocia a más nota en todas las ediciones**: entre unos 9 y 13 puntos por desviación típica,
  sea cual sea la especificación. Es la variable de interés con más relación con la nota.
- **La asistencia pesa igual en toda la década.** Haber faltado a clase se asocia a unos 17 o 18 puntos menos y
  cada nivel de impuntualidad a unos 10 a 13 puntos menos, en 2012 y en 2022. Se mantiene con más alumnos (sin
  exigir la pregunta de deberes) y con 25 países.
- **Los recursos de estudio se asocian a más nota, de forma estable**: unos 5 o 6 puntos por desviación típica
  (aproximadamente, por tener uno más de los seis recursos; entre 4,5 y 6,5 según la especificación). El cambio de 2012 a 2022 nunca
  se distingue de cero con los 12 países (va de 0,0 a 0,8 puntos), salvo al quitar Eslovaquia (1,5, p = 0,041). Por tramos, tener todos menos uno o los
  seis sigue asociado a más nota, y tener los seis añade poco sobre tener cinco.
- **Las conclusiones no dependen de los controles del centro.** Con la escasez de recursos los coeficientes no se
  mueven. Con el nivel socioeconómico medio del centro, el de los recursos baja algo (de 5,4-5,9 a 4,5-5,2), pero
  las conclusiones son las mismas.

## Resultados que hay que contar con cautela
- **La subida del compromiso de 2012 a 2022 es pequeña y frágil.** En el modelo de partida sube 1,5 puntos
  (p = 0,029). Es positiva en todas las comprobaciones (de 1,0 a 2,7 puntos), pero deja de distinguirse de cero al
  quitar Australia, Reino Unido, Hungría, Italia, Eslovaquia o Eslovenia, o con el nivel socioeconómico del centro.
  Además, viene del componente de deberes, el que peor se compara entre ediciones (ver la nota de compromiso).
  Se puede decir que la relación del compromiso con la nota se mantiene o sube algo, no que se haya reforzado.
- **El privado urbano grande en 2022 depende de Australia.** Con los 12 países, el coeficiente de los recursos de
  estudio en ese perfil sube unos 14 puntos de 2012 a 2022, y es lo que hace que los perfiles difieran entre sí en
  2022. Aguanta todas las comprobaciones (también por tramos y con otros controles) menos una: sin Australia, la
  subida baja a 6,8 puntos (p = 0,316) y los perfiles dejan de diferenciarse. Ver la nota de perfiles de centro.
- **Con 25 países la imagen de los recursos es algo distinta.** Su coeficiente sí sube de 2012 a 2022 (de 4,5 a 6,1,
  p = 0,002) y en 2022 los privados urbanos grandes y medianos quedan por encima de los públicos, sin depender de
  ningún país (tampoco de Australia). Es un indicio de un patrón más general, pero ese panel tiene otros países,
  otro índice de compromiso y no tiene 2018: no es el modelo de la aplicación.

## Lo que no cambia entre perfiles
- **El compromiso se asocia a la nota igual en todos los perfiles de centro**, y su cambio de 2012 a 2022 también
  es igual en todos. Ningún país quitado cambia esta conclusión con los 12 países.

## Cómo usar esta nota
- Si el usuario pregunta si un resultado es fiable, contestar con lo que aguanta y lo que no, en lenguaje sencillo.
- No presentar como hallazgo firme la subida del compromiso ni la del privado urbano grande.
- Origen: `notebooks/fase_3_modelado/03_robustez_regresion.ipynb`; todas las cifras en
  `data/processed/resultados_robustez.parquet`.
