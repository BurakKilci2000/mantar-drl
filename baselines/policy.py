"""Politika arayüzü (yöntem dokümanı, Tablo B.5).

PPO ajanı ve tüm karşılaştırma yöntemleri bu arayüzü uygular; evaluate.py
hangi yöntemi çalıştırdığını bilmeden hepsini aynı biçimde çağırır.
"""


class Policy:
    name = "policy"

    def act(self, observation):
        """Gözlemi alır, eylemi döndürür."""
        raise NotImplementedError
