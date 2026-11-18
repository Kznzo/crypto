"""ClipForge — transforme tes clips Twitch en vidéos TikTok, Reels, Shorts et YouTube."""

__version__ = "1.0.0"


def _use_system_certificates() -> None:
    """Connexions HTTPS fiables partout.

    Le Python de python.org sur Mac (et un antivirus qui inspecte le HTTPS sur Windows) provoque l'erreur
    « CERTIFICATE_VERIFY_FAILED : unable to get local issuer certificate ». On fait donc confiance aux
    certificats du système (trousseau du Mac, magasin de Windows) grâce à truststore ; à défaut, on se sert
    de la liste de certificats de certifi.
    """
    try:
        import truststore

        truststore.inject_into_ssl()
        return
    except Exception:
        pass
    try:
        import os

        import certifi

        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    except Exception:
        pass


_use_system_certificates()
