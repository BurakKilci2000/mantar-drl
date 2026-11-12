"""Politika arayüzü (yöntem dokümanı, Tablo B.5).

PPO ajanı ve tüm karşılaştırma yöntemleri bu arayüzü uygular; degerlendir.py
hangi yöntemi çalıştırdığını bilmeden hepsini aynı biçimde çağırır.
"""


class Politika:
    ad = "politika"

    def eylem_sec(self, gozlem):
        """Gözlemi alır, eylemi döndürür."""
        raise NotImplementedError
