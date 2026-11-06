import re
from collections import Counter
from datetime import date
from pathlib import Path
import tkinter as tk
from tkinter import filedialog


NIVELES_VALIDOS = {"INFO", "WARNING", "ERROR"}
PATRON_FECHA = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def analizar_linea(linea, fecha_actual):
    """Devuelve el registro válido y los motivos de invalidez de una línea."""
    original = linea.rstrip("\r\n")
    motivos = []

    nivel_match = re.match(r"^\[([^\]]*)\](.*)$", original)
    if nivel_match is None:
        return None, ["No contiene un nivel de severidad en el formato [NIVEL]."]

    nivel = nivel_match.group(1)
    resto = nivel_match.group(2)
    if nivel not in NIVELES_VALIDOS:
        motivos.append(
            f"Nivel de severidad no válido: {nivel!r}; "
            "se esperaba INFO, WARNING o ERROR."
        )

    if not resto or not resto[0].isspace():
        return None, motivos + ["Falta la fecha después del nivel de severidad."]

    campos = resto.strip().split(maxsplit=1)
    if not campos:
        return None, motivos + ["Falta la fecha después del nivel de severidad."]

    texto_fecha = campos[0]
    mensaje = campos[1].strip() if len(campos) > 1 else ""

    fecha_registro = None
    if not PATRON_FECHA.fullmatch(texto_fecha):
        motivos.append(
            f"Formato de fecha no válido: {texto_fecha!r}; "
            "se esperaba AAAA-MM-DD."
        )
    else:
        try:
            fecha_registro = date.fromisoformat(texto_fecha)
        except ValueError:
            motivos.append(f"Fecha imposible: {texto_fecha!r}.")
        else:
            if fecha_registro > fecha_actual:
                motivos.append(
                    f"Fecha posterior a la fecha actual: {texto_fecha!r}."
                )

    if not mensaje:
        motivos.append("El mensaje está ausente o vacío.")

    if motivos:
        return None, motivos

    return {"nivel": nivel, "mensaje": mensaje}, []


def analizar_archivo(ruta, fecha_actual=None):
    """Analiza el archivo y separa los registros válidos de las líneas inválidas."""
    if fecha_actual is None:
        fecha_actual = date.today()

    conteos = Counter()
    mensajes = {"WARNING": Counter(), "ERROR": Counter()}
    invalidas = []

    with Path(ruta).open("r", encoding="utf-8-sig") as archivo:
        for numero, linea in enumerate(archivo, start=1):
            registro, motivos = analizar_linea(linea, fecha_actual)
            if motivos:
                invalidas.append(
                    {
                        "numero": numero,
                        "texto": linea.rstrip("\r\n"),
                        "motivos": motivos,
                    }
                )
                continue

            conteos[registro["nivel"]] += 1
            if registro["nivel"] in mensajes:
                mensajes[registro["nivel"]][registro["mensaje"]] += 1

    return conteos, mensajes, invalidas


def imprimir_desglose(titulo, conteos):
    print(f"\n{titulo}:")
    if not conteos:
        print("  Sin registros válidos.")
        return

    for mensaje, cantidad in sorted(
        conteos.items(), key=lambda elemento: (-elemento[1], elemento[0].casefold())
    ):
        print(f"  {cantidad:>5}  {mensaje}")

    mayor_frecuencia = max(conteos.values())
    mas_frecuentes = [
        mensaje
        for mensaje, cantidad in conteos.items()
        if cantidad == mayor_frecuencia
    ]
    print(f"  Motivo(s) más frecuente(s), {mayor_frecuencia} registro(s):")
    for mensaje in sorted(mas_frecuentes, key=str.casefold):
        print(f"    - {mensaje}")


def imprimir_resumen(conteos, mensajes, invalidas):
    total = sum(conteos.values())
    print("\n========== Resumen de registros ==========")
    print(f"Total de eventos válidos: {total}")
    print("Eventos válidos por tipo:")
    for nivel in ("INFO", "WARNING", "ERROR"):
        print(f"  {nivel:<7} {conteos.get(nivel, 0)}")
    print(f"Líneas mal formateadas o incompletas: {len(invalidas)}")

    imprimir_desglose("Motivos de WARNING", mensajes["WARNING"])
    imprimir_desglose("Motivos de ERROR", mensajes["ERROR"])

    if invalidas:
        print("\nDetalle de líneas inválidas:")
        for invalida in invalidas:
            print(f"  Línea {invalida['numero']}: {invalida['texto']}")
            for motivo in invalida["motivos"]:
                print(f"    - {motivo}")


def seleccionar_archivo():
    ventana = tk.Tk()
    ventana.withdraw()
    try:
        return filedialog.askopenfilename(
            parent=ventana,
            title="Seleccionar archivo de registros",
            filetypes=[("Archivos de texto", "*.txt")],
        )
    finally:
        ventana.destroy()


def main():
    try:
        ruta = seleccionar_archivo()
    except tk.TclError as error:
        print(f"No se pudo abrir el selector de archivos: {error}")
        return 1

    if not ruta:
        print("No se seleccionó ningún archivo.")
        return 0

    try:
        conteos, mensajes, invalidas = analizar_archivo(ruta)
    except (OSError, UnicodeError) as error:
        print(f"No se pudo leer el archivo seleccionado: {error}")
        return 1

    print(f"Archivo analizado: {ruta}")
    imprimir_resumen(conteos, mensajes, invalidas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
