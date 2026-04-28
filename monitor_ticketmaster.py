import sys
import io
import time
import random
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

# Fix emoji/unicode output on Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TELEGRAM_TOKEN = "7971403571:AAEpC4o_o9v86x7moQl0lG5bzcXV-aB2M9c"
CHAT_IDS = ["1517464913", "5449322274"]
URL = "https://www.ticketmaster.com.br/event/enhypen-world-tour-blood-saga"

# Palavras ESPECÍFICAS que indicam ingressos disponíveis para compra
# Evitar palavras genéricas como "comprar" que aparecem no menu
AVAILABLE_KEYWORDS = [
    "selecionar ingresso",
    "adicionar ao carrinho",
    "selecionar setor",
    "escolha seu ingresso",
    "escolher ingresso",
    "comprar ingresso",
    "add to cart",
    "select ticket",
]

# Palavras que indicam ingressos ESGOTADOS
SOLD_OUT_KEYWORDS = [
    "esgotado",
    "sold out",
    "indisponível",
    "não disponível",
    "encerrado",
    "evento encerrado",
    "ingressos esgotados",
    "unavailable",
]


def send_telegram(message: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    success = True
    for chat_id in CHAT_IDS:
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code != 200:
                success = False
        except Exception as e:
            print(f"[ERRO] Telegram (chat {chat_id}): {e}")
            success = False
    return success


def create_driver() -> uc.Chrome:
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1280,800")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    driver = uc.Chrome(version_main=147, options=options)
    return driver


def check_tickets(driver: uc.Chrome) -> tuple[str, str]:
    """
    Returns: (status, matched_keyword)
    status: 'available', 'sold_out', or 'unknown'
    """
    try:
        driver.get(URL)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()

        for kw in SOLD_OUT_KEYWORDS:
            if kw in page_text:
                return "sold_out", kw

        for kw in AVAILABLE_KEYWORDS:
            if kw in page_text:
                return "available", kw

        return "unknown", ""
    except Exception as e:
        print(f"[ERRO] ao verificar pagina: {e}")
        return "error", ""


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def main():
    log("Iniciando monitor de ingressos - ENHYPEN WORLD TOUR BLOOD SAGA")
    log(f"URL: {URL}")

    ok = send_telegram(
        "🎫 <b>Monitor iniciado!</b>\n"
        "Monitorando ingressos do ENHYPEN WORLD TOUR BLOOD SAGA na Ticketmaster.\n"
        f"URL: {URL}"
    )
    if ok:
        log("Notificacao de inicio enviada ao Telegram com sucesso.")
    else:
        log("AVISO: falha ao enviar mensagem inicial ao Telegram.")

    driver = None
    check_count = 0

    try:
        driver = create_driver()
        log("Browser iniciado com sucesso.")

        while True:
            check_count += 1
            status, kw = check_tickets(driver)
            log(f"Verificacao #{check_count} - status: {status}" + (f' (keyword: "{kw}")' if kw else ""))

            if status == "available":
                msg = (
                    "🚨 <b>INGRESSOS DISPONÍVEIS!</b> 🚨\n\n"
                    "🎫 ENHYPEN WORLD TOUR BLOOD SAGA\n"
                    f"🔗 <a href=\"{URL}\">Comprar agora</a>\n\n"
                    "Corra antes que esgotem!"
                )
                if send_telegram(msg):
                    log("ALERTA enviado ao Telegram - ingressos disponiveis!")
                else:
                    log("ERRO ao enviar alerta ao Telegram!")

            elif status == "sold_out":
                log(f'Esgotado (detectado: "{kw}") - continuando monitoramento...')

            elif status == "unknown":
                log("Status desconhecido - aguardando pagina carregar (15s)...")
                time.sleep(15)

            elif status == "error":
                log("Erro ao carregar pagina - reiniciando o browser...")
                try:
                    driver.quit()
                except Exception:
                    pass
                time.sleep(5)
                driver = create_driver()
                log("Browser reiniciado.")

            delay = random.uniform(5, 8)
            log(f"Aguardando {delay:.1f}s ate proxima verificacao...")
            time.sleep(delay)

    except KeyboardInterrupt:
        log("Monitor encerrado pelo usuario.")
        send_telegram("⛔ Monitor encerrado manualmente.")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()
