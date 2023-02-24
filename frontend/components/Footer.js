import { Container, Typography, Link } from '@mui/material';
import GitHubIcon from '@mui/icons-material/GitHub'

export default function Footer() {
    return (
        <Container sx={{ mt: '1em' }}>
            <Typography textAlign="center" mt="1em">Built by <Link href="https://twitter.com/emilianobonassi" target="_blank" rel="noreferrer">emiliano.eth</Link></Typography>
            <Typography textAlign="center" mt="1em"><Link href="https://github.com/emilianobonassi/testnet-fyi" target="_blank" rel="noreferrer"><GitHubIcon/></Link></Typography>
        </Container>
    );
}