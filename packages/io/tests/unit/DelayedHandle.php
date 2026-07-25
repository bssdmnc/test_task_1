<?php

declare(strict_types=1);

namespace Psl\IO\Tests\Unit;

use Override;
use Psl\Async\CancellationTokenInterface;
use Psl\Async\NullCancellationToken;
use Psl\IO;

use function min;
use function strlen;
use function substr;

/**
 * A read handle that releases its payload in small chunks.
 *
 * Each read returns at most {@see $chunkSize} bytes, so a consumer that needs a
 * delimiter — such as {@see IO\Reader::readLine()} or {@see IO\Reader::readUntil()} —
 * is forced to issue several reads and stitch the result together across chunk
 * boundaries. This exercises the reader's internal buffering instead of letting a
 * single read satisfy the request.
 */
final class DelayedHandle implements IO\ReadHandleInterface
{
    use IO\ReadHandleConvenienceMethodsTrait;

    /**
     * @param string $data The payload to hand out.
     * @param positive-int $chunkSize Maximum number of bytes released per read.
     */
    public function __construct(
        private string $data,
        private readonly int $chunkSize = 1,
    ) {}

    #[Override]
    public function reachedEndOfDataSource(): bool
    {
        return $this->data === '';
    }

    /**
     * @param null|positive-int $maxBytes
     */
    #[Override]
    public function tryRead(null|int $maxBytes = null): string
    {
        if ($this->data === '') {
            return '';
        }

        $length = min($this->chunkSize, strlen($this->data));
        if ($maxBytes !== null) {
            $length = min($length, $maxBytes);
        }

        $chunk = substr($this->data, 0, $length);
        $this->data = substr($this->data, $length);

        return $chunk;
    }

    /**
     * @param null|positive-int $maxBytes
     */
    #[Override]
    public function read(
        null|int $maxBytes = null,
        CancellationTokenInterface $cancellation = new NullCancellationToken(),
    ): string {
        return $this->tryRead($maxBytes);
    }
}
