import { loginUrl } from "../api";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { CrosshairIcon } from "../components/CrosshairIcon";
import { Logo } from "../components/Logo";

export function LoginView() {
  return (
    <div className="login-screen">
      <Card className="login-card">
        <CrosshairIcon size={72} />
        <Logo size={32} />
        <p className="login-sub">
          Iniciá sesión con Steam para ver tu historial de partidas y line ups.
        </p>
        <Button as="a" href={loginUrl()} className="login-cta">
          Iniciar sesión con Steam
        </Button>
        <p className="login-fine">Al continuar aceptás los Términos y la Política de Privacidad.</p>
      </Card>
    </div>
  );
}
