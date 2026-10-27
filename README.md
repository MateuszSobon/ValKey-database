# Rozproszony ogranicznik liczby żądań z Valkey

Projekt: rozproszony rate limiter (np. 100 żądań na 60 sekund na klienta) oparty na Valkey, współdzielony przez wiele instancji aplikacji. Służy też do zbadania zachowania Valkey jako systemu rozproszonego: współbieżność, replikacja, partycjonowanie, awarie.

## Status

- [x] Pojedyncza instancja Valkey (WSL Ubuntu)
- [x] Fixed window (`INCR` + `EXPIRE` w transakcji)
- [x] Wersja naiwna (`GET` / `+1` / `SET`) i test współbieżny
- [x] Sliding window (sorted set + skrypt Lua)
- [ ] Wiele instancji aplikacji (min. 3)
- [ ] Klaster Valkey z replikami
- [ ] Eksperymenty z awariami i pomiary
- [ ] Raport techniczny i demo

## Wymagania

- Python 3.11+
- Valkey (serwer) w WSL Ubuntu
- Biblioteka kliencka: `valkey` (`pip install valkey`)

## Uruchomienie



## Konwencja nazw kluczy


## Algorytmy


## Licencja

Projekt edukacyjny.
