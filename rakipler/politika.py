"""Politika arayüzü (yöntem dokümanı, Tablo B.5).

PPO ajanı ve tüm karşılaştırma yöntemleri bu arayüzü uygular; degerlendir.py
hangi yöntemi çalıştırdığını bilmeden hepsini aynı biçimde çağırır.
"""


class Politika:
    ad = "politika"

    def sifirla(self, tohum: int) -> None:
        """Her bölümün başında çağrılır. Rastgelelik kullanan politikalar (örneklemeli PPO) burada
        kendi rastgele sayı üretecini tohumlar; böylece aynı tohum aynı sonucu verir."""

    def eylem_sec(self, gozlem):
        """Gözlemi alır, eylemi döndürür."""
        raise NotImplementedError
